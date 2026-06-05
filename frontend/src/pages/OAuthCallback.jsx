import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';

const OAuthCallback = () => {
  const [searchParams] = useSearchParams();
  const { loginWithOAuth } = useAuth();
  const navigate = useNavigate();
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const handleAuth = async () => {
      const code = searchParams.get('code');

      if (!code) {
        navigate('/login', { replace: true });
        return;
      }

      // 10-second timeout
      const timeoutId = setTimeout(() => {
        if (active) {
          controller.abort();
          setErrorMsg('Authentication timed out. Please try again.');
        }
      }, 10000);

      try {
        const response = await api.post('/api/v1/auth/oauth/exchange', 
          { code },
          { signal: controller.signal }
        );
        clearTimeout(timeoutId);
        if (!active) return;
        const { access_token, refresh_token } = response.data;
        await loginWithOAuth(access_token, refresh_token);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        clearTimeout(timeoutId);
        if (!active) return;
        if (err.name === 'CanceledError' || err.name === 'AbortError') {
          return; // Already handled by timeout
        }
        console.error('OAuth exchange failed:', err);
        setErrorMsg(err.response?.data?.detail || 'Authentication failed. Please try again.');
      }
    };
    handleAuth();

    return () => {
      active = false;
      controller.abort();
    };
  }, [searchParams, loginWithOAuth, navigate]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#090d16', flexDirection: 'column', gap: '1rem', fontFamily: 'Inter, sans-serif' }}>
      {errorMsg ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div style={{ color: '#ef4444', fontSize: '1.2rem', marginBottom: '1rem' }}>{errorMsg}</div>
          <Link to="/login" style={{ color: '#8b5cf6', textDecoration: 'underline' }}>Back to Login</Link>
        </div>
      ) : (
        <div style={{ color: '#94a3b8', fontSize: '1rem' }}>Completing login...</div>
      )}
    </div>
  );
};

export default OAuthCallback;
