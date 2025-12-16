import { useState, useEffect } from 'react';
import { outletsAPI } from '../../services/api/outlets';
import './OrgCard.css';

export default function OrgCard() {
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Fetch organization statistics
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoadingStats(true);
      const response = await outletsAPI.getOrganizationStats();
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch organization stats:', error);
      setStats({
        products_count: 0,
        recipes_count: 0,
        users_count: 0,
        outlets_count: 0,
        imports_count: 0
      });
    } finally {
      setLoadingStats(false);
    }
  };

  return (
    <div className="org-card">
      <div className="org-card-header">
        <div className="org-card-icon">🏛️</div>
        <div className="org-card-info">
          <h3 className="org-card-name">{stats?.organization_name || 'Organization'}</h3>
          <p className="org-card-subtitle">Organization Overview</p>
        </div>
      </div>

      {/* Statistics */}
      <div className="org-card-stats">
        {loadingStats ? (
          <div className="stats-loading">Loading stats...</div>
        ) : (
          <>
            <div className="stat-item">
              <span className="stat-icon">🏢</span>
              <div className="stat-info">
                <span className="stat-value">{stats?.outlets_count || 0}</span>
                <span className="stat-label">Outlets</span>
              </div>
            </div>

            <div className="stat-item">
              <span className="stat-icon">📦</span>
              <div className="stat-info">
                <span className="stat-value">{stats?.products_count || 0}</span>
                <span className="stat-label">Products</span>
              </div>
            </div>

            <div className="stat-item">
              <span className="stat-icon">📋</span>
              <div className="stat-info">
                <span className="stat-value">{stats?.recipes_count || 0}</span>
                <span className="stat-label">Recipes</span>
              </div>
            </div>

            <div className="stat-item">
              <span className="stat-icon">👥</span>
              <div className="stat-info">
                <span className="stat-value">{stats?.users_count || 0}</span>
                <span className="stat-label">Users</span>
              </div>
            </div>

            <div className="stat-item">
              <span className="stat-icon">📥</span>
              <div className="stat-info">
                <span className="stat-value">{stats?.imports_count || 0}</span>
                <span className="stat-label">Imports</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
