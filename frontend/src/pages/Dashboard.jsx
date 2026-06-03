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
  const [expiresAt, setExpiresAt] = useState('');
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
      const payload = {
        original_url: originalUrl,
        ...(customAlias.trim() && { custom_alias: customAlias.trim() }),
        ...(expiresAt && { expires_at: new Date(expiresAt).toISOString() }),
      };

      const response = await api.post('/api/v1/links', payload);
      setCreateSuccess(`Shortened link created: ${response.data.short_code}`);
      
      // Reset form
      setOriginalUrl('');
      setCustomAlias('');
      setExpiresAt('');
      
      // Refresh list
      fetchLinks();
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
      
      fetchLinks();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete link');
    }
  };

  // Prepare chart data: fill missing days with 0 or map directly
  const chartData = analytics?.clicks_per_day?.map(item => ({
    name: new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    Clicks: item.click_count,
  })) || [];

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
                  <label htmlFor="dash-expiry">Expiration Date (Optional)</label>
                  <input
                    id="dash-expiry"
                    type="datetime-local"
                    value={expiresAt}
                    onChange={(e) => setExpiresAt(e.target.value)}
                  />
                </div>
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
