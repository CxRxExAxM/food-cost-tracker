import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import axios from '../../lib/axios';
import './SuperAdmin.css';

export default function SuperAdminOrganizationDetail() {
  const { orgId } = useParams();
  const navigate = useNavigate();
  const [organization, setOrganization] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrganizationDetail();
  }, [orgId]);

  const fetchOrganizationDetail = async () => {
    try {
      const response = await axios.get(`/super-admin/organizations/${orgId}`);
      setOrganization(response.data);
    } catch (error) {
      console.error('Error fetching organization detail:', error);
      alert('Error loading organization');
      navigate('/super-admin/organizations');
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

  const getRoleBadgeColor = (role) => {
    const colors = {
      admin: '#f59e0b',
      chef: '#3b82f6',
      viewer: '#6b7280'
    };
    return colors[role] || '#6b7280';
  };

  if (loading) {
    return <div className="loading">Loading organization details...</div>;
  }

  if (!organization) {
    return <div className="loading">Organization not found</div>;
  }

  return (
    <div className="super-admin-organization-detail">
      <div className="detail-header">
        <div>
          <Link to="/super-admin/organizations" className="back-link">
            ← Back to Organizations
          </Link>
          <h1>{organization.name}</h1>
          <div className="org-meta">
            <span className="org-slug">{organization.slug}</span>
            <span
              className="org-tier-badge"
              style={{ backgroundColor: getTierColor(organization.subscription_tier) }}
            >
              {organization.subscription_tier}
            </span>
            {organization.subscription_status === 'suspended' && (
              <span className="status-badge suspended">SUSPENDED</span>
            )}
          </div>
        </div>
      </div>

      {/* Organization Stats */}
      <div className="detail-stats">
        <div className="stat-card">
          <div className="stat-value">{organization.users_count || 0}</div>
          <div className="stat-label">Users</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{organization.outlets_count || 0}</div>
          <div className="stat-label">Outlets</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{organization.products_count || 0}</div>
          <div className="stat-label">Products</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{organization.recipes_count || 0}</div>
          <div className="stat-label">Recipes</div>
        </div>
      </div>

      {/* Users Table */}
      <div className="detail-section">
        <h2>Users ({organization.users.length})</h2>
        {organization.users.length === 0 ? (
          <div className="empty-state">No users found</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Username</th>
                <th>Full Name</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {organization.users.map((user) => (
                <tr key={user.id} className={!user.is_active ? 'inactive-row' : ''}>
                  <td>{user.email}</td>
                  <td>{user.username}</td>
                  <td>{user.full_name || '-'}</td>
                  <td>
                    <span
                      className="role-badge"
                      style={{ backgroundColor: getRoleBadgeColor(user.role) }}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <button className="action-btn" disabled>
                      Edit
                    </button>
                    <button className="action-btn" disabled>
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Outlets Table */}
      <div className="detail-section">
        <h2>Outlets ({organization.outlets.length})</h2>
        {organization.outlets.length === 0 ? (
          <div className="empty-state">No outlets found</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Location</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {organization.outlets.map((outlet) => (
                <tr key={outlet.id} className={!outlet.is_active ? 'inactive-row' : ''}>
                  <td>{outlet.name}</td>
                  <td>{outlet.location || '-'}</td>
                  <td>
                    <span className={`status-badge ${outlet.is_active ? 'active' : 'inactive'}`}>
                      {outlet.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
