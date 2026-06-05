import React, { useState } from 'react';
import api from '../api/axios';
import { parseExpiryDateTime } from '../utils/parseExpiry';

const Landing = () => {
  const [originalUrl, setOriginalUrl] = useState('');
  const [customAlias, setCustomAlias] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [expiryTime, setExpiryTime] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [shortUrl, setShortUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setShortUrl('');
    setCopied(false);

    try {
      let parsedExpiry = null;
      try {
        parsedExpiry = parseExpiryDateTime(expiryDate, expiryTime);
      } catch (dateErr) {
        setError(dateErr.message);
        setLoading(false);
        return;
      }

      const payload = {
        original_url: originalUrl,
        ...(customAlias.trim() && { custom_alias: customAlias.trim() }),
        ...(parsedExpiry && { expires_at: parsedExpiry }),
      };

      const response = await api.post('/api/v1/links', payload);
      
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      setShortUrl(`${apiBaseUrl}/${response.data.short_code}`);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred while shortening the URL.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(shortUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="container" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div className="hero-section">
        <h1 className="hero-title">Simplify your link management</h1>
        <p className="hero-subtitle">
          Brief.ly is a clean, modern URL shortener built to provide fast redirections and comprehensive, real-time analytics dashboards.
        </p>

        <div className="shorten-box">
          {error && <div className="alert alert-danger">{error}</div>}
          
          <form onSubmit={handleSubmit}>
            <div className="shorten-form-row">
              <input
                type="url"
                required
                placeholder="Paste your long link here (e.g. https://example.com/very/long/path)"
                value={originalUrl}
                onChange={(e) => setOriginalUrl(e.target.value)}
              />
              <button type="submit" disabled={loading} className="btn btn-primary">
                {loading ? 'Shortening...' : 'Shorten URL'}
              </button>
            </div>

            <div className="advanced-options-toggle">
              <button
                type="button"
                className="toggle-btn"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  style={{
                    transform: showAdvanced ? 'rotate(90deg)' : 'none',
                    transition: 'transform 0.15s ease',
                  }}
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                Advanced settings (alias & expiration)
              </button>
            </div>

            {showAdvanced && (
              <div className="advanced-options">
                <div className="form-group">
                  <label htmlFor="alias">Custom Alias (Optional)</label>
                  <input
                    id="alias"
                    type="text"
                    placeholder="e.g. custom-name"
                    value={customAlias}
                    onChange={(e) => setCustomAlias(e.target.value)}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', gridColumn: 'span 2' }}>
                  <div className="form-group">
                    <label htmlFor="expiry-date">Expiration Date (Optional)</label>
                    <input
                      id="expiry-date"
                      type="date"
                      value={expiryDate}
                      onChange={(e) => setExpiryDate(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="expiry-time">Expiration Time (Optional)</label>
                    <input
                      id="expiry-time"
                      type="time"
                      value={expiryTime}
                      onChange={(e) => setExpiryTime(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}
          </form>

          {shortUrl && (
            <div className="result-box">
              <div>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem' }}>
                  Your shortened link is ready:
                </span>
                <a href={shortUrl} target="_blank" rel="noopener noreferrer" className="result-url">
                  {shortUrl}
                </a>
              </div>
              <button onClick={handleCopy} className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Landing;
