import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <nav className="navbar">
      <div className="container navbar-container">
        <Link to="/" className="navbar-brand" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: 'var(--gold-accent)' }}
          >
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          <span style={{ fontSize: '1.25rem', fontWeight: '700', letterSpacing: '-0.02em', color: 'var(--text-heading)' }}>
            Brief.ly
          </span>
        </Link>

        <div className="navbar-links">
          <NavLink
            to="/"
            className={({ isActive }) => (isActive ? 'navbar-link active' : 'navbar-link')}
            end
          >
            Shorten
          </NavLink>

          {user ? (
            <>
              <NavLink
                to="/dashboard"
                className={({ isActive }) => (isActive ? 'navbar-link active' : 'navbar-link')}
              >
                Dashboard
              </NavLink>
              <span className="navbar-link" style={{ cursor: 'default', opacity: 0.7, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {user.email}
              </span>
              <button 
                onClick={handleLogout} 
                className="btn btn-secondary" 
                style={{ padding: '0.4rem 1rem', fontSize: '0.8rem', borderRadius: 'var(--radius-sm)' }}
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="navbar-link" style={{ marginRight: '0.5rem' }}>
                Login
              </Link>
              <Link 
                to="/register" 
                className="btn btn-primary" 
                style={{ padding: '0.4rem 1rem', fontSize: '0.8rem', borderRadius: 'var(--radius-sm)' }}
              >
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
