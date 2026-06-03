import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const OAuthCallback = () => {
  const [searchParams] = useSearchParams();
  const { loginWithOAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');

    if (accessToken && refreshToken) {
      // Save tokens and load auth profile
      loginWithOAuth(accessToken, refreshToken);
      navigate('/dashboard', { replace: true });
    } else {
      // If tokens are missing, redirect to login
      navigate('/login', { replace: true });
    }
  }, [searchParams, loginWithOAuth, navigate]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#090d16' }}>
      <div style={{ color: '#94a3b8', fontSize: '1rem', fontFamily: 'Inter, sans-serif' }}>Completing login...</div>
    </div>
  );
};

export default OAuthCallback;
