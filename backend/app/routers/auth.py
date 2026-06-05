"""
app/routers/auth.py
────────────────────
Authentication endpoints — register, login, refresh, GitHub OAuth, get-me.

All endpoints live under /api/v1/auth/ prefix (set in main.py).

GitHub OAuth flow (how it works):
1. Frontend sends user to GET /api/v1/auth/github
2. We redirect to GitHub's authorization page
3. User approves on GitHub → GitHub redirects to our callback URL with a ?code=
4. GET /api/v1/auth/github/callback receives the code
5. We exchange code for GitHub access token (server-to-server)
6. We fetch the user's GitHub profile (id, email)
7. We create/find our user and return a JWT
8. We redirect the frontend to /?token=<jwt> so it can save the token
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.token import AccessToken, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserLogin, UserResponse, OAuthExchangeRequest
from app.services.auth_service import AuthService, create_oauth_exchange_token, decode_token

# Instantiate OAuth client once at module level
oauth = OAuth()
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register with email and password",
    description="Creates a new account and returns JWT access + refresh tokens. User is immediately logged in.",
)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> Token:
    service = AuthService(db)
    return await service.register(data)


@router.post(
    "/login",
    response_model=Token,
    summary="Login with email and password",
    description="Returns JWT access + refresh tokens on successful authentication. Rate limited.",
)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    await _check_login_rate_limit(request)
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.post(
    "/refresh",
    response_model=AccessToken,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token. Refresh token itself is not rotated.",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> AccessToken:
    """Body: {"refresh_token": "eyJ..."}"""
    service = AuthService(db)
    new_access_token = await service.refresh_access_token(data.refresh_token)
    return AccessToken(access_token=new_access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Returns the profile of the currently authenticated user.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


# ── GitHub OAuth ──────────────────────────────────────────────────────────────

@router.get(
    "/github",
    summary="Initiate GitHub OAuth login",
    description="Redirects the user to GitHub's authorization page. Open this URL in a browser.",
)
async def github_login(request: Request):
    """
    Redirects to GitHub OAuth authorization page.
    The user will be asked to approve access to their email on GitHub.
    """
    redirect_uri = settings.github_redirect_uri
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback",
    description="Handles the redirect from GitHub after user approval. Returns a short-lived exchange code.",
)
async def github_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    GitHub redirects here after the user approves the OAuth app.
    We exchange the code for a token, fetch the user's profile,
    then redirect the frontend with a short-lived exchange code.
    """
    from fastapi import HTTPException
    import httpx
    import uuid

    try:
        token = await oauth.github.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed — invalid or expired code")

    # Fetch GitHub user profile
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        user_resp = await client.get("https://api.github.com/user", headers=headers)
        emails_resp = await client.get("https://api.github.com/user/emails", headers=headers)

    github_user = user_resp.json()
    emails = emails_resp.json()

    # Get primary verified email
    email = next(
        (e["email"] for e in emails if e.get("primary") and e.get("verified")),
        github_user.get("email"),
    )

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from GitHub account")

    github_id = str(github_user["id"])
    service = AuthService(db)
    jwt_tokens = await service.get_or_create_github_user(github_id=github_id, email=email)

    # Decode user ID from tokens and generate the one-time exchange token
    payload = decode_token(jwt_tokens.access_token)
    user_uuid = uuid.UUID(payload.sub)
    exchange_code = create_oauth_exchange_token(user_uuid)

    # Redirect frontend with exchange code
    redirect_url = f"{settings.frontend_url}/oauth/callback?code={exchange_code}"
    return RedirectResponse(url=redirect_url)


@router.post(
    "/oauth/exchange",
    response_model=Token,
    summary="Exchange OAuth code for tokens",
    description="Trade a short-lived exchange code for a full JWT access/refresh token pair.",
)
async def oauth_exchange(
    data: OAuthExchangeRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    service = AuthService(db)
    return await service.exchange_oauth_token(data.code)


async def _check_login_rate_limit(request: Request) -> None:
    """Limit login attempts by IP to prevent brute-force attacks."""
    from fastapi import HTTPException
    from app.main import redis_client
    if not redis_client:
        return

    try:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:login:{client_ip}"
        limit = 10
        ttl = 900 # 15 minutes

        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local ttl = tonumber(ARGV[2])
        local val = redis.call('incr', key)
        if val == 1 then
            redis.call('expire', key, ttl)
        end
        if val > limit then
            return 0
        end
        return 1
        """
        allowed = await redis_client.eval(lua_script, 1, key, limit, ttl)

        if allowed == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again in 15 minutes.",
                headers={"Retry-After": str(ttl)},
            )
    except HTTPException:
        raise
    except Exception as e:
        import structlog
        log = structlog.get_logger()
        log.warning("ratelimit.login_redis_error", error=str(e))
        return  # Fail open
