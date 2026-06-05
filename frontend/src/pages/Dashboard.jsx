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
import { QRCodeSVG } from 'qrcode.react';
import api from '../api/axios';
import { parseExpiryDateTime } from '../utils/parseExpiry';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { user } = useAuth();
  const [links, setLinks] = useState([]);
  const [loadingLinks, setLoadingLinks] = useState(true);
  
  // Tab control
  const [currentTab, setCurrentTab] = useState('links');
  
  // Custom Toast Notifications
  const [toasts, setToasts] = useState([]);
  const addToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [qrTarget, setQrTarget] = useState(null);

  // Create Link form inside dashboard
  const [originalUrl, setOriginalUrl] = useState('');
  const [customAlias, setCustomAlias] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [expiryTime, setExpiryTime] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  // Rate limit state (fetched from backend)
  const [rateLimitData, setRateLimitData] = useState(null);
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

  const handleSelectLinkAndNavigate = (link) => {
    handleSelectLink(link);
    addToast(`Loaded analytics for /${link.short_code}`, 'success');
    setCurrentTab('analytics');
  };

  const handleShowAllAnalytics = () => {
    handleSelectLink(null);
    addToast("Loaded global click analytics", "success");
    setCurrentTab('analytics');
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
      addToast('Failed to load shortened links', 'danger');
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
        addToast('Selected link no longer exists', 'danger');
        setTimeout(() => {
          handleSelectLink(null);
        }, 3000);
      } else {
        setAnalyticsError('Could not load analytics data.');
        addToast('Could not load analytics', 'danger');
      }
    } finally {
      setLoadingAnalytics(false);
    }
  }, [selectedLink]);

  // Fetch real rate limit usage from backend
  const fetchRateLimit = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/links/rate-limit');
      setRateLimitData(res.data);
    } catch {
      // silently fail — not critical
    }
  }, []);

  useEffect(() => {
    document.title = "Dashboard — Brief.ly";
  }, []);

  useEffect(() => {
    fetchLinks(page);
  }, [page]);

  // Initial analytics fetch + 30-second polling
  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000);
    return () => clearInterval(interval);
  }, [selectedLink, fetchAnalytics]);

  // Refresh analytics when user switches to the analytics tab
  useEffect(() => {
    if (currentTab === 'analytics') {
      fetchAnalytics();
    }
  }, [currentTab]);

  // Fetch rate limit on mount + refresh after creating a link
  useEffect(() => {
    fetchRateLimit();
  }, [fetchRateLimit]);

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
        addToast(dateErr.message, 'danger');
        setCreating(false);
        return;
      }

      const payload = {
        original_url: originalUrl,
        ...(customAlias.trim() && { custom_alias: customAlias.trim() }),
        ...(parsedExpiry && { expires_at: parsedExpiry }),
      };

      const response = await api.post('/api/v1/links', payload);
      const newShortCode = response.data.short_code;
      setCreateSuccess(`Shortened link created: ${newShortCode}`);
      addToast(`Shortened link created: /${newShortCode}`, 'success');
      
      // Reset form
      setOriginalUrl('');
      setCustomAlias('');
      setExpiryDate('');
      setExpiryTime('');
      setShowCreateModal(false);
      
      // Refresh list and analytics
      fetchLinks(page);
      fetchAnalytics();
      fetchRateLimit();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to create link';
      setCreateError(msg);
      addToast(msg, 'danger');
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
      addToast(`Link /${shortCode} copied to clipboard!`, 'success');
      setTimeout(() => setCopiedCode(null), 2000);
    });
  };

  const confirmDeleteLink = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/api/v1/links/${deleteTarget}`);
      addToast(`Link /${deleteTarget} deleted successfully`, 'success');
      
      // If we deleted the currently selected link, reset selection
      if (selectedLink?.short_code === deleteTarget) {
        handleSelectLink(null);
      }
      
      // Refresh list and analytics
      const newPage = (links.length === 1 && page > 1) ? page - 1 : page;
      setPage(newPage);
      fetchLinks(newPage);
      fetchAnalytics();
      fetchRateLimit();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to delete link';
      addToast(msg, 'danger');
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

  // Tab: Link Management view
  const renderLinksTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '500' }}>My Shortened Links</h3>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
              onClick={handleShowAllAnalytics}
            >
              Show All Analytics
            </button>
            <button
              className="btn btn-primary"
              style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}
              onClick={() => setShowCreateModal(true)}
            >
              + Shorten Link
            </button>
          </div>
        </div>

        {loadingLinks ? (
          <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>Loading links...</div>
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
                  className={`card link-item`}
                  style={{
                    cursor: 'pointer',
                    padding: '1.25rem 1.5rem',
                    borderColor: isSelected ? 'var(--gold-accent)' : 'var(--border)',
                    backgroundColor: isSelected ? 'var(--elevated-surface)' : 'var(--card-bg)',
                    boxShadow: isSelected ? 'var(--glow-gold)' : 'none',
                  }}
                  onClick={() => handleSelectLinkAndNavigate(link)}
                >
                  <div className="link-details">
                    <span
                      className="link-short-url"
                      style={{
                        color: isSelected ? 'var(--gold-accent)' : 'var(--text-heading)',
                        fontWeight: '600'
                      }}
                    >
                      /{link.short_code}
                    </span>
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
                      onClick={(e) => {
                        e.stopPropagation();
                        setQrTarget(link.short_code);
                      }}
                      className="btn btn-secondary"
                      style={{
                        padding: '0.4rem 0.75rem',
                        fontSize: '0.75rem',
                        border: '1px solid rgba(212,175,55,0.2)'
                      }}
                    >
                      QR
                    </button>
                    <button
                      onClick={(e) => handleCopy(link.short_code, e)}
                      className="btn btn-secondary"
                      style={{
                        padding: '0.4rem 0.75rem',
                        fontSize: '0.75rem',
                        color: copiedCode === link.short_code ? 'var(--success)' : 'var(--text-body)',
                        borderColor: copiedCode === link.short_code ? 'var(--success)' : 'var(--border)',
                      }}
                    >
                      {copiedCode === link.short_code ? 'Copied!' : 'Copy'}
                    </button>
                    <button
                      onClick={(e) => handleDeleteLink(link.short_code, e)}
                      className="btn btn-secondary"
                      style={{
                        padding: '0.4rem 0.75rem',
                        fontSize: '0.75rem',
                        color: 'var(--danger)',
                        borderColor: 'rgba(226, 92, 92, 0.2)',
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <button
              disabled={page === 1}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
              onClick={() => setPage(prev => Math.max(prev - 1, 1))}
            >
              Previous
            </button>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
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
  );

  // Tab: Analytics view
  const renderAnalyticsTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '500' }}>
            {selectedLink ? `Analytics for /${selectedLink.short_code}` : 'Global Click Analytics'}
          </h3>
          {selectedLink && (
            <button
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
              onClick={() => {
                handleSelectLink(null);
                addToast("Loaded global click analytics", "success");
              }}
            >
              Reset to Global View
            </button>
          )}
        </div>

        {loadingAnalytics ? (
          <div style={{ textAlign: 'center', padding: '4.5rem 0', color: 'var(--text-muted)' }}>Loading analytics data...</div>
        ) : analyticsError ? (
          <div className="alert alert-danger">{analyticsError}</div>
        ) : (
          <div className="analytics-section">
            
            {/* Aggregate stat metrics */}
            {!selectedLink && (
              <div className="analytics-cards">
                <div className="stat-card">
                  <div className="stat-val">{analytics.total_clicks}</div>
                  <div className="stat-label">Total Clicks</div>
                </div>
                <div className="stat-card">
                  <div className="stat-val">{totalLinks}</div>
                  <div className="stat-label">Active Links</div>
                </div>
              </div>
            )}

            {selectedLink && (
              <div className="analytics-cards">
                <div className="stat-card">
                  <div className="stat-val">{analytics.total_clicks || 0}</div>
                  <div className="stat-label">Link Clicks</div>
                </div>
                <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <div style={{ wordBreak: 'break-all', fontSize: '0.9rem', color: 'var(--text-heading)', fontWeight: '500', marginBottom: '0.25rem' }}>
                    {selectedLink.original_url}
                  </div>
                  <div className="stat-label">Destination URL</div>
                </div>
              </div>
            )}

            {/* Recharts chart */}
            <div style={{
              backgroundColor: '#0B0B0B',
              border: '1px solid rgba(212,175,55,0.12)',
              borderRadius: 'var(--radius-md)',
              padding: '1.5rem',
              boxShadow: 'inset 0 0 20px rgba(0,0,0,0.8)'
            }}>
              <h4 className="small-label" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Clicks Over Last 30 Days</h4>
              {chartData.length === 0 ? (
                <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-disabled)' }}>
                  No click records found for this period
                </div>
              ) : (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <LineChart data={chartData} margin={{ left: -25, right: 10, top: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#151515" />
                      <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} />
                      <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#151515',
                          borderColor: 'rgba(212,175,55,0.15)',
                          color: '#F8F8F8',
                          fontSize: '0.85rem',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="Clicks"
                        stroke="var(--gold-accent)"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5, fill: 'var(--gold-accent)', stroke: '#050505', strokeWidth: 2 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Referrers & Countries Flex */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
              
              {/* Top Referrers */}
              <div className="card" style={{ padding: '1.5rem' }}>
                <h4 className="small-label" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Top Referrers</h4>
                {analytics.top_referrers?.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-disabled)', padding: '1rem 0' }}>No referrer data available</div>
                ) : (
                  <div className="table-container">
                    {analytics.top_referrers?.map((ref, idx) => (
                      <div key={idx} className="table-row">
                        <span>{ref.referrer || 'Direct'}</span>
                        <span>{ref.click_count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Top Countries */}
              <div className="card" style={{ padding: '1.5rem' }}>
                <h4 className="small-label" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Top Countries</h4>
                {analytics.top_countries?.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-disabled)', padding: '1rem 0' }}>No country data available</div>
                ) : (
                  <div className="table-container">
                    {analytics.top_countries?.map((c, idx) => (
                      <div key={idx} className="table-row">
                        <span>{c.country || 'Unknown'}</span>
                        <span>{c.click_count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );

  // Tab: Profile view
  const renderProfileTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="card">
        <h3 className="mb-6" style={{ fontSize: '1.25rem', fontWeight: '500' }}>User Profile</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '2rem' }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--gold-dark) 0%, var(--gold-accent) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.35rem',
            color: '#050505',
            fontWeight: 'bold',
            boxShadow: 'var(--glow-gold)'
          }}>
            {user?.email ? user.email[0].toUpperCase() : 'U'}
          </div>
          <div>
            <h4 style={{ fontSize: '1.1rem', color: 'var(--text-heading)', fontWeight: '600' }}>{user?.email || 'N/A'}</h4>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
          <div>
            <span className="small-label" style={{ display: 'block', marginBottom: '0.25rem' }}>Member Since</span>
            <div style={{ fontSize: '0.95rem', color: 'var(--text-heading)' }}>
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
                : 'N/A'}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="mb-6" style={{ fontSize: '1.25rem', fontWeight: '500' }}>Link Creation Usage</h3>
        {rateLimitData ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
              <span>Hourly Link Creation</span>
              <span style={{ color: 'var(--gold-accent)', fontWeight: '500' }}>
                {rateLimitData.used} / {rateLimitData.limit} per hour
              </span>
            </div>
            <div style={{ height: '6px', backgroundColor: 'var(--bg-primary)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{
                width: `${Math.min((rateLimitData.used / rateLimitData.limit) * 100, 100)}%`,
                height: '100%',
                background: 'linear-gradient(90deg, var(--gold-dark), var(--gold-accent))',
                borderRadius: '3px'
              }}></div>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              Resets in {Math.ceil(rateLimitData.resets_in_seconds / 60)} minutes
            </p>
          </div>
        ) : (
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <p>Up to 50 link creations per hour.</p>
            <p style={{ marginTop: '0.35rem' }}>{totalLinks} active link{totalLinks !== 1 ? 's' : ''} in your account.</p>
          </div>
        )}
      </div>
    </div>
  );



  return (
    <div className="container" style={{ minHeight: '85vh', paddingBottom: '4rem' }}>
      
      {/* Control Center Navbar / Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: '1.5rem', paddingTop: '3.5rem', marginBottom: '2.5rem' }}>
        <div>
          <h2 className="serif-heading" style={{ fontSize: '2.2rem', fontWeight: '400', color: 'var(--text-heading)', marginBottom: '0.35rem' }}>
            Dashboard
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Manage your shortcodes and view real-time click telemetry</p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.25rem', backgroundColor: 'var(--bg-secondary)', padding: '0.25rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
          <button
            className={`btn ${currentTab === 'links' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ padding: '0.4rem 1.1rem', fontSize: '0.8rem' }}
            onClick={() => setCurrentTab('links')}
          >
            Links
          </button>
          <button
            className={`btn ${currentTab === 'analytics' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ padding: '0.4rem 1.1rem', fontSize: '0.8rem' }}
            onClick={() => setCurrentTab('analytics')}
          >
            Analytics
          </button>
          <button
            className={`btn ${currentTab === 'profile' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ padding: '0.4rem 1.1rem', fontSize: '0.8rem' }}
            onClick={() => setCurrentTab('profile')}
          >
            Profile
          </button>
        </div>
      </div>

      {/* Main Tab Render */}
      <div className="dashboard-grid">
        {currentTab === 'links' && renderLinksTab()}
        {currentTab === 'analytics' && renderAnalyticsTab()}
        {currentTab === 'profile' && renderProfileTab()}
      </div>

      {/* Create Link Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '500', color: 'var(--text-heading)', marginBottom: '1.5rem' }}>
              Shorten a New Link
            </h3>
            
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

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.75rem' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowCreateModal(false)}
                  style={{ flex: 1 }}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={creating} 
                  className="btn btn-primary" 
                  style={{ flex: 1 }}
                >
                  {creating ? 'Creating...' : 'Shorten Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '500', color: 'var(--text-heading)', marginBottom: '0.75rem' }}>
              Delete short URL?
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-body)', marginBottom: '1.75rem', lineHeight: '1.6' }}>
              Are you sure you want to delete <strong style={{ color: 'var(--text-heading)' }}>/{deleteTarget}</strong>? This action cannot be undone. All associated click analytics will be permanently erased.
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

      {/* QR Code Modal — generated locally via qrcode.react, no external API */}
      {qrTarget && (
        <div className="modal-overlay" onClick={() => setQrTarget(null)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '400px', textAlign: 'center' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '500', color: 'var(--text-heading)', marginBottom: '1.25rem' }}>
              QR Code for /{qrTarget}
            </h3>
            <div style={{
              background: '#0B0B0B',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '1.5rem',
              display: 'inline-block',
              marginBottom: '1.5rem',
              boxShadow: 'inset 0 0 10px rgba(0,0,0,0.8)'
            }}>
              <QRCodeSVG
                id="qr-code-svg"
                value={`${apiBaseUrl}/${qrTarget}`}
                size={200}
                fgColor="#D4AF37"
                bgColor="#0B0B0B"
              />
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-body)', marginBottom: '1.5rem', wordBreak: 'break-all' }}>
              Point your camera to redirect to:<br/>
              <strong style={{ color: 'var(--gold-accent)' }}>{`${apiBaseUrl}/${qrTarget}`}</strong>
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setQrTarget(null)}
                style={{ flex: 1, padding: '0.6rem 1.25rem', fontSize: '0.9rem' }}
              >
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  const svgEl = document.getElementById('qr-code-svg');
                  if (!svgEl) return;
                  const serializer = new XMLSerializer();
                  const svgStr = serializer.serializeToString(svgEl);
                  const blob = new Blob([svgStr], { type: 'image/svg+xml' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `qrcode-${qrTarget}.svg`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  URL.revokeObjectURL(url);
                  addToast('QR Code downloaded!', 'success');
                }}
                style={{ flex: 1, padding: '0.6rem 1.25rem', fontSize: '0.9rem' }}
              >
                Download SVG
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Toast Notification Container */}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span>{t.message}</span>
            <button
              onClick={() => setToasts(prev => prev.filter(item => item.id !== t.id))}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '1rem',
                marginLeft: '1rem'
              }}
            >
              &times;
            </button>
          </div>
        ))}
      </div>

    </div>
  );
};

export default Dashboard;
