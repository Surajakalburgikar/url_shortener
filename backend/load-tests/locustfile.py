import random
from locust import HttpUser, task, between

class URLShortenerUser(HttpUser):
    # Simulated wait time between tasks: 1 to 3 seconds
    wait_time = between(1, 3)

    def on_start(self):
        """Executed when a simulated user starts running."""
        self.headers = {}
        self.email = f"loadtest_{random.randint(100000, 999999)}@example.com"
        self.password = "password123"
        self.short_codes = ["jbdvuW"]  # Default short code fallback

        # Register and log in the user to obtain token
        self._register_and_login()

    def _register_and_login(self):
        """Registers a new user and signs in to fetch the JWT access token."""
        # 1. Register
        register_payload = {"email": self.email, "password": self.password}
        with self.client.post(
            "/api/v1/auth/register",
            json=register_payload,
            catch_response=True
        ) as response:
            if response.status_code in [201, 409]:  # 201 Created or 409 Already Exists
                response.success()
            else:
                response.failure(f"Registration failed with code: {response.status_code}")

        # 2. Login
        login_payload = {"email": self.email, "password": self.password}
        with self.client.post(
            "/api/v1/auth/login",
            json=login_payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                if access_token:
                    self.headers = {"Authorization": f"Bearer {access_token}"}
                    response.success()
                else:
                    response.failure("Login response missing access_token")
            else:
                response.failure(f"Login failed with code: {response.status_code}")

    @task(70)
    def test_redirect(self):
        """Simulate hot path URL redirection (70% weight)."""
        short_code = random.choice(self.short_codes)
        with self.client.get(
            f"/{short_code}",
            allow_redirects=False,
            catch_response=True
        ) as response:
            # We expect a 307 Temporary Redirect
            if response.status_code == 307:
                response.success()
            elif response.status_code == 404:
                # 404 is acceptable during load test if short code does not exist in DB
                response.success()
            else:
                response.failure(f"Redirection failed with code: {response.status_code}")

    @task(20)
    def test_create_link(self):
        """Simulate creating a shortened link (20% weight)."""
        payload = {
            "original_url": f"https://www.google.com/search?q={random.randint(1, 100000)}",
            "custom_alias": None,
            "expires_at": None
        }
        with self.client.post(
            "/api/v1/links",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                link_data = response.json()
                short_code = link_data.get("short_code")
                if short_code:
                    self.short_codes.append(short_code)
                response.success()
            else:
                response.failure(f"Link creation failed with code: {response.status_code}")

    @task(10)
    def test_analytics(self):
        """Simulate checking personal link analytics (10% weight)."""
        with self.client.get(
            "/api/v1/analytics/me",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Analytics check failed with code: {response.status_code}")
