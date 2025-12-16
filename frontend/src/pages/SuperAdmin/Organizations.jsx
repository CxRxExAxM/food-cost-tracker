import { useState, useEffect } from 'react';
import axios from '../../lib/axios';
import './SuperAdmin.css';

export default function SuperAdminOrganizations() {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');

  useEffect(() => {
    fetchOrganizations();
  }, [search, tierFilter]);

  const fetchOrganizations = async () => {
    try {
      const params = {};
      if (search) params.search = search;
      if (tierFilter) params.tier = tierFilter;

      const response = await axios.get('/super-admin/organizations', { params });
      setOrganizations(response.data);
    } catch (error) {
      console.error('Error fetching organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTierColor = (tier) => {
    const colors = {
      free: '#6b7280',
      basic: '#3b82f6',
      pro: '#8b5cf6',
      enterprise: '#f59e0b'
    };
    return colors[tier] || '#6b7280';
  };

  if (loading) {
    return <div className="loading">Loading organizations...</div>;
  }

  return (
    <div className="super-admin-organizations">
      <div className="organizations-header">
        <div>
          <h1>Organizations</h1>
          <p className="subtitle">Manage all platform organizations</p>
        </div>
        <button className="create-org-btn">+ Create Organization</button>
      </div>

      <div className="filters" style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
        <input
          type="text"
          placeholder="Search organizations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1,
            padding: '0.75rem',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '1rem'
          }}
        />
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          style={{
            padding: '0.75rem',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '1rem',
            minWidth: '150px'
          }}
        >
          <option value="">All Tiers</option>
          <option value="free">Free</option>
          <option value="basic">Basic</option>
          <option value="pro">Pro</option>
          <option value="enterprise">Enterprise</option>
        </select>
      </div>

      <div className="organizations-grid">
        {organizations.map((org) => (
          <div key={org.id} className="org-card">
            <div className="org-header">
              <div className="org-info">
                <h3>{org.name}</h3>
                <div className="org-slug">{org.slug}</div>
              </div>
              <div
                className="org-tier"
                style={{ backgroundColor: getTierColor(org.subscription_tier) }}
              >
                {org.subscription_tier}
              </div>
            </div>

            <div className="org-stats">
              <div className="org-stat">
                <div className="org-stat-value">{org.users_count || 0}</div>
                <div className="org-stat-label">Users</div>
              </div>
              <div className="org-stat">
                <div className="org-stat-value">{org.outlets_count || 0}</div>
                <div className="org-stat-label">Outlets</div>
              </div>
              <div className="org-stat">
                <div className="org-stat-value">{org.products_count || 0}</div>
                <div className="org-stat-label">Products</div>
              </div>
              <div className="org-stat">
                <div className="org-stat-value">{org.recipes_count || 0}</div>
                <div className="org-stat-label">Recipes</div>
              </div>
            </div>

            <div className="org-actions">
              <button>View Details</button>
              <button>Edit Tier</button>
              <button style={{ color: '#dc2626' }}>Suspend</button>
            </div>
          </div>
        ))}
      </div>

      {organizations.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#6b7280' }}>
          No organizations found
        </div>
      )}
    </div>
  );
}
