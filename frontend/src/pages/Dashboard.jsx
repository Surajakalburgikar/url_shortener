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
import { parseExpiryDateTime } from '../utils/parseExpiry';

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
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [copiedCode, setCopiedCode] = useState(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [totalLinks, setTotalLinks] = useState(0);
  const PAGE_SIZE = 10;

  const [selectedLink, setSelectedLink] = useState(null);

  const handleSelectLink = (link) => {
    if (link) {
      setSelectedLink(link);
      localStorage.setItem('selected_short_code', link.short_code);
    } else {
      setSelectedLink(null);
      localStorage.removeItem('selected_short_code');
    }
  };
  
  // Analytics state
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(true);
  const [analyticsError, setAnalyticsError] = useState('');

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  // Fetch all user links
  const fetchLinks = useCallback(async (targetPage = page) => {
    setLoadingLinks(true);
    try {
      const response = await api.get('/api/v1/links', {
        params: { page: targetPage, page_size: PAGE_SIZE },
      });
      const fetchedLinks = response.data.items || [];
      setLinks(fetchedLinks);
      setTotalLinks(response.data.total || 0);
      
      const storedShortCode = localStorage.getItem('selected_short_code');
      if (storedShortCode) {
        const matchedLink = fetchedLinks.find(link => link.short_code === storedShortCode);
        if (matchedLink) {
          setSelectedLink(matchedLink);
        }
      }
    } catch (err) {
      console.error('Failed to fetch links:', err);
    } finally {
      setLoadingLinks(false);
    }
  }, [page]);

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
      if (selectedLink && (err.response?.status === 404 || err.response?.status === 403)) {
        setAnalyticsError('Selected link no longer exists. Returning to global analytics view.');
        setTimeout(() => {
          handleSelectLink(null);
        }, 3000);
      } else {
        setAnalyticsError('Could not load analytics data.');
      }
    } finally {
      setLoadingAnalytics(false);
    }
  }, [selectedLink]);

  useEffect(() => {
    document.title = "Dashboard — Brief.ly";
  }, []);

  useEffect(() => {
    fetchLinks(page);
  }, [page]);

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
      try {
        parsedExpiry = parseExpiryDateTime(expiryDate, expiryTime);
      } catch (dateErr) {
        setCreateError(dateErr.message);
        setCreating(false);
        return;
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
      fetchLinks(page);
      fetchAnalytics();
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Failed to create link');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteLink = (shortCode, e) => {
    e.stopPropagation(); // Prevent selection trigger
    setDeleteTarget(shortCode);
  };

  const handleCopy = (shortCode, e) => {
    e.stopPropagation();
    const shortUrl = `${apiBaseUrl}/${shortCode}`;
    navigator.clipboard.writeText(shortUrl).then(() => {
      setCopiedCode(shortCode);
      setTimeout(() => setCopiedCode(null), 2000);
    });
  };

  const confirmDeleteLink = async () => {
    if (!deleteTarget) return;
    setDeleteError('');
    try {
      await api.delete(`/api/v1/links/${deleteTarget}`);
      
      // If we deleted the currently selected link, reset selection
      if (selectedLink?.short_code === deleteTarget) {
        handleSelectLink(null);
      }
      
      // Refresh list and analytics
      const newPage = (links.length === 1 && page > 1) ? page - 1 : page;
      setPage(newPage);
      fetchLinks(newPage);
      fetchAnalytics();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Failed to delete link');
    } finally {
      setDeleteTarget(null);
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
                  <input
                    id="dash-expiry-date"
                    type="date"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group" style={{ marginTop: '0.5rem' }}>
                <label htmlFor="dash-expiry-time">Expiration Time (Optional)</label>
                <input
                  id="dash-expiry-time"
                  type="time"
                  value={expiryTime}
                  onChange={(e) => setExpiryTime(e.target.value)}
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
                onClick={() => handleSelectLink(null)}
              >
                Show All Analytics
              </button>
            </div>

            {deleteError && (
              <div className="alert alert-danger" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <span>{deleteError}</span>
                <button
                  onClick={() => setDeleteError('')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    fontSize: '1.25rem',
                    lineHeight: '1',
                    padding: '0 0.5rem',
                  }}
                >
                  &times;
                </button>
              </div>
            )}

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
                      onClick={() => handleSelectLink(link)}
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
                      <div className="link-actions" style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={(e) => handleCopy(link.short_code, e)}
                          className="btn btn-secondary"
                          style={{
                            padding: '0.4rem 0.6rem',
                            fontSize: '0.8rem',
                            color: copiedCode === link.short_code ? 'var(--success)' : 'var(--text-secondary)',
                            borderColor: copiedCode === link.short_code ? 'var(--success)' : 'var(--border-color)',
                          }}
                        >
                          {copiedCode === link.short_code ? 'Copied!' : 'Copy'}
                        </button>
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

            {/* Pagination UI */}
            {totalLinks > PAGE_SIZE && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <button
                  disabled={page === 1}
                  className="btn btn-secondary"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                  onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                >
                  Previous
                </button>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Page {page} of {Math.ceil(totalLinks / PAGE_SIZE)} ({totalLinks} total links)
                </span>
                <button
                  disabled={page * PAGE_SIZE >= totalLinks}
                  className="btn btn-secondary"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                  onClick={() => setPage(prev => prev + 1)}
                >
                  Next
                </button>
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

      {deleteTarget && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: '#0a0a0a',
            border: '1px solid #1f1f1f',
            borderRadius: '12px',
            padding: '2rem',
            width: '100%',
            maxWidth: '440px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#ffffff', marginBottom: '0.75rem' }}>
              Delete short URL?
            </h3>
            <p style={{ fontSize: '0.9rem', color: '#a3a3a3', marginBottom: '1.5rem', lineHeight: '1.5' }}>
              Are you sure you want to delete <strong style={{ color: '#ffffff' }}>/{deleteTarget}</strong>? This action cannot be undone. All associated click analytics will be permanently erased.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setDeleteTarget(null)}
                style={{ padding: '0.6rem 1.25rem', fontSize: '0.9rem' }}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={confirmDeleteLink}
                style={{ padding: '0.6rem 1.25rem', fontSize: '0.9rem' }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
