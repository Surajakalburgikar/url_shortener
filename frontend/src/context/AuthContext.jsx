import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch the current user profile
  const checkAuth = async () => {
    try {
      const response = await api.get('/api/v1/auth/me');
      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const parseError = (error, defaultMsg) => {
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
      return detail.map(d => d.msg).join(', ');
    }
    if (typeof detail === 'object' && detail !== null) {
      return JSON.stringify(detail);
    }
    return detail || defaultMsg;
  };

  const login = async (email, password) => {
    setLoading(true);
    try {
      await api.post('/api/v1/auth/login', { email, password });
      
      // Fetch user profile immediately (cookies set automatically by backend)
      const profileResponse = await api.get('/api/v1/auth/me');
      setUser(profileResponse.data);
      return profileResponse.data;
    } catch (error) {
      throw parseError(error, 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const register = async (email, password) => {
    setLoading(true);
    try {
      await api.post('/api/v1/auth/register', { email, password });
      
      // Fetch user profile immediately (cookies set automatically by backend)
      const profileResponse = await api.get('/api/v1/auth/me');
      setUser(profileResponse.data);
      return profileResponse.data;
    } catch (error) {
      throw parseError(error, 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('Logout request failed:', error);
    } finally {
      localStorage.removeItem('selected_short_code');
      setUser(null);
    }
  };

  const loginWithOAuth = async () => {
    setLoading(true);
    try {
      // Reload auth state (cookies set automatically by backend)
      await checkAuth();
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        loginWithOAuth,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
