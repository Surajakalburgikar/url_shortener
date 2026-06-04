import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import api from '../api/axios';

const Dashboard = () => {
  const [links, setLinks] = useState([]);
  const [loadingLinks, setLoadingLinks] = useState(true);
  
  // Create Link form inside dashboard
  const [originalUrl, setOriginalUrl] = useState('');
  const [customAlias, setCustomAlias] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [expiryTime, setExpiryTime] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');

  // Selection state
  // null = Global/All Links, otherwise holds selected link object
  const [selectedLink, setSelectedLink] = useState(null);
  
  // Analytics state
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(true);
  const [analyticsError, setAnalyticsError] = useState('');

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  // Fetch all user links
  const fetchLinks = async () => {
    setLoadingLinks(true);
    try {
      const response = await api.get('/api/v1/links', {
        params: { page: 1, page_size: 100 },
      });
      setLinks(response.data.items || []);
    } catch (err) {
      console.error('Failed to fetch links:', err);
    } finally {
      setLoadingLinks(false);
    }
  };

  // Fetch analytics (either global or specific link)
  const fetchAnalytics = useCallback(async () => {
    setLoadingAnalytics(true);
    setAnalyticsError('');
    try {
      let endpoint = '/api/v1/analytics/me';
      if (selectedLink) {
        endpoint = `/api/v1/analytics/${selectedLink.short_code}`;
      }
      
      const response = await api.get(endpoint);
      setAnalytics(response.data);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setAnalyticsError('Could not load analytics data.');
    } finally {
      setLoadingAnalytics(false);
    }
  }, [selectedLink]);

  useEffect(() => {
    fetchLinks();
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [selectedLink, fetchAnalytics]);

  const handleCreateLink = async (e) => {
    e.preventDefault();
    setCreating(true);
    setCreateError('');
    setCreateSuccess('');

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
          setCreateError('Invalid date format. Please use YYYY-MM-DD or select using the calendar.');
          setCreating(false);
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
          setCreateError('Expiration date must be in the future.');
          setCreating(false);
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
      setCreateSuccess(`Shortened link created: ${response.data.short_code}`);
      
      // Reset form
      setOriginalUrl('');
      setCustomAlias('');
      setExpiryDate('');
      setExpiryTime('');
      
      // Refresh list and analytics
      fetchLinks();
      fetchAnalytics();
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Failed to create link');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteLink = async (shortCode, e) => {
    e.stopPropagation(); // Prevent selection trigger
    if (!window.confirm(`Are you sure you want to delete /${shortCode}?`)) {
      return;
    }

    try {
      await api.delete(`/api/v1/links/${shortCode}`);
      
      // If we deleted the currently selected link, reset selection
      if (selectedLink?.short_code === shortCode) {
        setSelectedLink(null);
      }
      
      // Refresh list and analytics
      fetchLinks();
      fetchAnalytics();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete link');
    }
  };

  // Prepare chart data: fill missing days of the last 30 days with 0 clicks
  const chartData = React.useMemo(() => {
    if (!analytics || !analytics.clicks_per_day) return [];
    
    // Map existing click count values by date string (YYYY-MM-DD)
    const clickMap = {};
    analytics.clicks_per_day.forEach(item => {
      clickMap[item.date] = item.click_count;
    });

    const data = [];
    const today = new Date();

    // Generate the last 30 days continuous timeline
    for (let i = 29; i >= 0; i--) {
      const d = new Date();
      d.setDate(today.getDate() - i);
      
      // Format to YYYY-MM-DD in local time
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const dateStr = `${year}-${month}-${day}`;
      
      const count = clickMap[dateStr] || 0;
      
      data.push({
        name: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        Clicks: count,
      });
    }

    return data;
  }, [analytics]);

  return (
    <div className="container">
      <div className="dashboard-grid">
        
        {/* Left Side: Create form & Link List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {/* Dashboard Shortener Form */}
          <div className="card">
            <h3 className="mb-6" style={{ fontSize: '1.25rem' }}>Shorten a New Link</h3>
            
            {createError && <div className="alert alert-danger">{createError}</div>}
            {createSuccess && <div className="alert alert-success">{createSuccess}</div>}

            <form onSubmit={handleCreateLink}>
              <div className="form-group">
                <label htmlFor="dash-url">Destination URL</label>
                <input
                  id="dash-url"
                  type="url"
                  required
                  placeholder="https://example.com/long-page-path"
                  value={originalUrl}
                  onChange={(e) => setOriginalUrl(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label htmlFor="dash-alias">Custom Alias (Optional)</label>
                  <input
                    id="dash-alias"
                    type="text"
                    placeholder="e.g. promo-code"
                    value={customAlias}
                    onChange={(e) => setCustomAlias(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="dash-expiry-date">Expiration Date (Optional)</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      id="dash-expiry-date"
                      type="text"
                      placeholder="YYYY-MM-DD"
                      value={expiryDate}
                      onChange={(e) => setExpiryDate(e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: '0 0.75rem', display: 'flex', alignItems: 'center' }}
                      onClick={() => {
                        try { document.getElementById('dash-date-picker').showPicker(); } catch (e) {}
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
                    id="dash-date-picker"
                    type="date"
                    style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}
                    onChange={(e) => { if (e.target.value) setExpiryDate(e.target.value); }}
                  />
                </div>
              </div>

              <div className="form-group" style={{ marginTop: '0.5rem' }}>
                <label htmlFor="dash-expiry-time">Expiration Time (Optional)</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    id="dash-expiry-time"
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
                      try { document.getElementById('dash-time-picker').showPicker(); } catch (e) {}
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                  </button>
                </div>
                <input
                  id="dash-time-picker"
                  type="time"
                  style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}
                  onChange={(e) => { if (e.target.value) setExpiryTime(e.target.value); }}
                />
              </div>

              <button type="submit" disabled={creating} className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }}>
                {creating ? 'Creating...' : 'Shorten Link'}
              </button>
            </form>
          </div>

          {/* Links List */}
          <div className="card" style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.25rem' }}>My Shortened Links</h3>
              <button
                className={`btn btn-secondary ${!selectedLink ? 'active' : ''}`}
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                onClick={() => setSelectedLink(null)}
              >
                Show All Analytics
              </button>
            </div>

            {loadingLinks ? (
              <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-secondary)' }}>Loading links...</div>
            ) : links.length === 0 ? (
              <div className="empty-state">
                <h3>No links yet</h3>
                <p>Shorten your first destination URL above to start gathering metrics!</p>
              </div>
            ) : (
              <div className="links-list">
                {links.map((link) => {
                  const isSelected = selectedLink?.short_code === link.short_code;
                  return (
                    <div
                      key={link.id}
                      className={`card link-item ${isSelected ? 'selected' : ''}`}
                      style={{
                        cursor: 'pointer',
                        padding: '1rem',
                        borderColor: isSelected ? 'var(--primary)' : 'var(--border-color)',
                        backgroundColor: isSelected ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                      }}
                      onClick={() => setSelectedLink(link)}
                    >
                      <div className="link-details">
                        <a
                          href={`${apiBaseUrl}/${link.short_code}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="link-short-url"
                          style={{
                            color: isSelected ? 'var(--primary)' : 'var(--text-primary)',
                            textDecoration: 'none',
                            fontWeight: '600'
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          /{link.short_code}
                        </a>
                        <div className="link-orig-url">{link.original_url}</div>
                        <div className="link-meta">
                          <span>Created {new Date(link.created_at).toLocaleDateString()}</span>
                          {link.expires_at && (
                            <span style={{ color: new Date(link.expires_at) < new Date() ? 'var(--danger)' : 'var(--text-muted)' }}>
                              Expires: {new Date(link.expires_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="link-actions">
                        <button
                          onClick={(e) => handleDeleteLink(link.short_code, e)}
                          className="btn btn-secondary"
                          style={{
                            padding: '0.4rem 0.6rem',
                            fontSize: '0.8rem',
                            color: 'var(--danger)',
                            borderColor: 'rgba(239, 68, 68, 0.2)',
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Analytics charts & tables */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          <div className="card">
            <h3 className="mb-6" style={{ fontSize: '1.25rem' }}>
              {selectedLink ? `Analytics for /${selectedLink.short_code}` : 'Global Click Analytics'}
            </h3>

            {loadingAnalytics ? (
              <div style={{ textAlign: 'center', padding: '4rem 0', color: 'var(--text-secondary)' }}>Loading analytics data...</div>
            ) : analyticsError ? (
              <div className="alert alert-danger">{analyticsError}</div>
            ) : (
              <div className="analytics-section">
                
                {/* Aggregate stat metrics (only on Global/Me view) */}
                {!selectedLink && (
                  <div className="analytics-cards">
                    <div className="stat-card">
                      <div className="stat-val">{analytics.total_clicks}</div>
                      <div className="stat-label">Total Clicks</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-val">{links.length}</div>
                      <div className="stat-label">Active Links</div>
                    </div>
                  </div>
                )}

                {/* Recharts chart */}
                <div>
                  <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Clicks Over Last 30 Days</h4>
                  {chartData.length === 0 ? (
                    <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                      No click records found for this period
                    </div>
                  ) : (
                    <div style={{ width: '100%', height: 200 }}>
                      <ResponsiveContainer>
                        <LineChart data={chartData} margin={{ left: -25, right: 10, top: 10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} />
                          <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} allowDecimals={false} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: 'var(--bg-secondary)',
                              borderColor: 'var(--border-color)',
                              color: 'var(--text-primary)',
                              fontSize: '0.85rem',
                              borderRadius: 'var(--radius-sm)',
                            }}
                          />
                          <Line
                            type="monotone"
                            dataKey="Clicks"
                            stroke="var(--primary)"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>

                {/* Top Referrers */}
                <div style={{ marginTop: '1rem' }}>
                  <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Top Referrers</h4>
                  {analytics.top_referrers?.length === 0 ? (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No referrer data</div>
                  ) : (
                    <div>
                      {analytics.top_referrers?.map((ref, idx) => (
                        <div key={idx} className="table-row">
                          <span>{ref.referrer}</span>
                          <span>{ref.click_count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Top Countries */}
                <div style={{ marginTop: '1rem' }}>
                  <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Top Countries</h4>
                  {analytics.top_countries?.length === 0 ? (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No country data</div>
                  ) : (
                    <div>
                      {analytics.top_countries?.map((c, idx) => (
                        <div key={idx} className="table-row">
                          <span>{c.country}</span>
                          <span>{c.click_count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
          
        </div>

      </div>
    </div>
  );
};

export default Dashboard;
