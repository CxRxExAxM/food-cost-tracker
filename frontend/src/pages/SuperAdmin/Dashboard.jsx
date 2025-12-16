import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import axios from '../../lib/axios';
import './SuperAdmin.css';

export default function SuperAdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('/super-admin/stats/overview');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching platform stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading platform statistics...</div>;
  }

  if (!stats) {
    return <div className="error">Failed to load statistics</div>;
  }

  const tierColors = {
    free: '#6b7280',
    basic: '#3b82f6',
    pro: '#8b5cf6',
    enterprise: '#f59e0b'
  };

  return (
    <div className="super-admin-dashboard">
      <div className="super-admin-nav">
        <div className="super-admin-tabs">
          <Link
            to="/super-admin"
            className={`super-admin-tab ${location.pathname === '/super-admin' ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link
            to="/super-admin/organizations"
            className={`super-admin-tab ${location.pathname === '/super-admin/organizations' ? 'active' : ''}`}
          >
            Organizations
          </Link>
        </div>
        <Link to="/" className="return-to-main-btn">
          ← Return to Main Site
        </Link>
      </div>

      <h1>Platform Overview</h1>
      <p className="subtitle">RestauranTek Platform Statistics</p>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">🏢</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_organizations}</div>
            <div className="stat-label">Organizations</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_users}</div>
            <div className="stat-label">Total Users</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🏪</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_outlets}</div>
            <div className="stat-label">Outlets</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📦</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_products}</div>
            <div className="stat-label">Products</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📝</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_recipes}</div>
            <div className="stat-label">Recipes</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <div className="stat-value">{stats.active_organizations}</div>
            <div className="stat-label">Active Orgs</div>
          </div>
        </div>
      </div>

      <div className="tier-breakdown">
        <h2>Organizations by Tier</h2>
        <div className="tier-grid">
          {Object.entries(stats.orgs_by_tier).map(([tier, count]) => (
            <div key={tier} className="tier-card">
              <div
                className="tier-badge"
                style={{ backgroundColor: tierColors[tier] || '#6b7280' }}
              >
                {tier.toUpperCase()}
              </div>
              <div className="tier-count">{count}</div>
              <div className="tier-label">organizations</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
