import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';

const OAuthCallback = () => {
  const [searchParams] = useSearchParams();
  const { loginWithOAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handleAuth = async () => {
      const code = searchParams.get('code');

      if (code) {
        try {
          const response = await api.post('/api/v1/auth/oauth/exchange', { code });
          const { access_token, refresh_token } = response.data;
          await loginWithOAuth(access_token, refresh_token);
          navigate('/dashboard', { replace: true });
        } catch (err) {
          console.error('OAuth exchange failed:', err);
          navigate('/login', { replace: true });
        }
      } else {
        // If code is missing, redirect to login
        navigate('/login', { replace: true });
      }
    };
    handleAuth();
  }, [searchParams, loginWithOAuth, navigate]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#090d16' }}>
      <div style={{ color: '#94a3b8', fontSize: '1rem', fontFamily: 'Inter, sans-serif' }}>Completing login...</div>
    </div>
  );
};

export default OAuthCallback;
