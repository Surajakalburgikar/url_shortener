import React, { useState } from 'react';
import api from '../api/axios';

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
      if (expiryDate.trim()) {
        const cleanedDate = expiryDate.trim();
        let date = null;

        // Try YYYY-MM-DD
        const yyyymmdd = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/.exec(cleanedDate);
        if (yyyymmdd) {
          const year = parseInt(yyyymmdd[1], 10);
          const month = parseInt(yyyymmdd[2], 10) - 1;
          const day = parseInt(yyyymmdd[3], 10);
          date = new Date(year, month, day);
        } else {
          // Try DD-MM-YYYY or DD/MM/YYYY
          const ddmmyyyy = /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/.exec(cleanedDate);
          if (ddmmyyyy) {
            const day = parseInt(ddmmyyyy[1], 10);
            const month = parseInt(ddmmyyyy[2], 10) - 1;
            const year = parseInt(ddmmyyyy[3], 10);
            date = new Date(year, month, day);
          } else {
            // Standard parse fallback
            date = new Date(cleanedDate);
          }
        }

        if (!date || isNaN(date.getTime())) {
          setError('Invalid date format. Please use YYYY-MM-DD or select using the calendar.');
          setLoading(false);
          return;
        }

        // Apply time if provided
        if (expiryTime.trim()) {
          const timeParts = /^(\d{1,2}):(\d{2})$/.exec(expiryTime.trim());
          if (timeParts) {
            const hours = parseInt(timeParts[1], 10);
            const minutes = parseInt(timeParts[2], 10);
            date.setHours(hours, minutes, 0, 0);
          } else {
            const timeVal = new Date(`1970-01-01T${expiryTime.trim()}`);
            if (!isNaN(timeVal.getTime())) {
              date.setHours(timeVal.getHours(), timeVal.getMinutes(), 0, 0);
            }
          }
        } else {
          // Time is optional — default to end of that day (23:59:59)
          date.setHours(23, 59, 59, 999);
        }

        // Validate future date
        if (date.getTime() <= Date.now()) {
          setError('Expiration date must be in the future.');
          setLoading(false);
          return;
        }

        parsedExpiry = date.toISOString();
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
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        id="expiry-date"
                        type="text"
                        placeholder="YYYY-MM-DD (e.g. 2026-12-31)"
                        value={expiryDate}
                        onChange={(e) => setExpiryDate(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '0 0.75rem', display: 'flex', alignItems: 'center' }}
                        onClick={() => {
                          try { document.getElementById('landing-date-picker').showPicker(); } catch (e) {}
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                          <line x1="16" y1="2" x2="16" y2="6"></line>
                          <line x1="8" y1="2" x2="8" y2="6"></line>
                          <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                      </button>
                    </div>
                    <input
                      id="landing-date-picker"
                      type="date"
                      style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}
                      onChange={(e) => { if (e.target.value) setExpiryDate(e.target.value); }}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="expiry-time">Expiration Time (Optional)</label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        id="expiry-time"
                        type="text"
                        placeholder="HH:MM (e.g. 14:30)"
                        value={expiryTime}
                        onChange={(e) => setExpiryTime(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '0 0.75rem', display: 'flex', alignItems: 'center' }}
                        onClick={() => {
                          try { document.getElementById('landing-time-picker').showPicker(); } catch (e) {}
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                      </button>
                    </div>
                    <input
                      id="landing-time-picker"
                      type="time"
                      style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}
                      onChange={(e) => { if (e.target.value) setExpiryTime(e.target.value); }}
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
