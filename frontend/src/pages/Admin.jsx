import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Settings, Building2, Users, X, Edit, BarChart3, Trash2 } from 'lucide-react';
import Navigation from '../components/Navigation';
import './Admin.css';

function Admin() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [orgStats, setOrgStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    subscription_tier: 'free',
    subscription_status: 'active',
    contact_email: '',
    contact_phone: ''
  });
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Check if user is admin, redirect if not
  useEffect(() => {
    if (!isAdmin()) {
      navigate('/');
    }
  }, [isAdmin, navigate]);

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/organizations', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch organizations');
      }

      const data = await response.json();
      setOrganizations(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching organizations:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrgStats = async (orgId) => {
    try {
      setLoadingStats(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/organizations/${orgId}/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch organization stats');
      }

      const data = await response.json();
      setOrgStats(data);
    } catch (err) {
      console.error('Error fetching organization stats:', err);
      alert('Failed to load organization stats');
    } finally {
      setLoadingStats(false);
    }
  };

  const handleCreateOrg = () => {
    setFormData({
      name: '',
      slug: '',
      subscription_tier: 'free',
      subscription_status: 'active',
      contact_email: '',
      contact_phone: ''
    });
    setFormErrors({});
    setShowCreateModal(true);
  };

  const handleEditOrg = (org) => {
    setSelectedOrg(org);
    setFormData({
      name: org.name,
      slug: org.slug,
      subscription_tier: org.subscription_tier,
      subscription_status: org.subscription_status,
      contact_email: org.contact_email || '',
      contact_phone: org.contact_phone || ''
    });
    setFormErrors({});
    setShowEditModal(true);
  };

  const handleViewStats = async (org) => {
    setSelectedOrg(org);
    setShowStatsModal(true);
    await fetchOrgStats(org.id);
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.name.trim()) {
      errors.name = 'Organization name is required';
    }

    if (!formData.slug.trim()) {
      errors.slug = 'Slug is required';
    } else if (!/^[a-z0-9-]+$/.test(formData.slug)) {
      errors.slug = 'Slug can only contain lowercase letters, numbers, and hyphens';
    }

    if (formData.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact_email)) {
      errors.contact_email = 'Invalid email format';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmitCreate = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setSubmitting(true);
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create organization');
      }

      await fetchOrganizations();
      setShowCreateModal(false);
      alert('Organization created successfully!');
    } catch (err) {
      console.error('Error creating organization:', err);
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitEdit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setSubmitting(true);
      const token = localStorage.getItem('token');

      // Only send fields that can be updated
      const updateData = {
        name: formData.name,
        subscription_tier: formData.subscription_tier,
        subscription_status: formData.subscription_status,
        contact_email: formData.contact_email || null,
        contact_phone: formData.contact_phone || null,
      };

      const response = await fetch(`http://localhost:8000/organizations/${selectedOrg.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update organization');
      }

      await fetchOrganizations();
      setShowEditModal(false);
      alert('Organization updated successfully!');
    } catch (err) {
      console.error('Error updating organization:', err);
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteOrg = async (org) => {
    if (!confirm(`Are you sure you want to delete "${org.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/organizations/${org.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete organization');
      }

      await fetchOrganizations();
      alert('Organization deleted successfully!');
    } catch (err) {
      console.error('Error deleting organization:', err);
      alert(err.message);
    }
  };

  const closeAllModals = () => {
    setShowCreateModal(false);
    setShowEditModal(false);
    setShowStatsModal(false);
    setSelectedOrg(null);
    setOrgStats(null);
  };

  return (
    <>
      <Navigation />
      <div className="admin">
        <div className="admin-container">
          <header className="admin-header">
            <div className="header-title">
              <Settings className="header-icon" size={32} />
              <div>
                <h1>Admin Panel</h1>
                <p>System administration and organization management</p>
              </div>
            </div>
          </header>

        <div className="admin-content">
          {/* Admin nav cards */}
          <div className="admin-nav-cards">
            <div className="nav-card active">
              <Building2 className="card-icon" size={32} />
              <h2>Organizations</h2>
              <p>Manage organizations, tiers, and subscription limits</p>
            </div>

            <div className="nav-card disabled">
              <Users className="card-icon" size={32} />
              <h2>Global Users</h2>
              <p>View all users across organizations</p>
              <span className="coming-soon">Coming Soon</span>
            </div>
          </div>

          {/* Organizations section */}
          <div className="admin-section">
            <div className="section-header">
              <h2>Organizations</h2>
              <button className="btn btn-primary" onClick={handleCreateOrg}>
                <Building2 size={18} />
                <span>New Organization</span>
              </button>
            </div>

            {loading && (
              <div className="loading-state">
                <div className="loading-spinner-enhanced"></div>
                <p>Loading organizations...</p>
              </div>
            )}

            {error && (
              <div className="error-state">
                <p>Error: {error}</p>
                <button className="btn" onClick={fetchOrganizations}>
                  Retry
                </button>
              </div>
            )}

            {!loading && !error && organizations.length === 0 && (
              <div className="empty-state">
                <Building2 size={64} className="empty-icon" />
                <h3>No organizations yet</h3>
                <p>Create your first organization to get started</p>
                <button className="btn btn-primary" onClick={handleCreateOrg}>
                  Create Organization
                </button>
              </div>
            )}

            {!loading && !error && organizations.length > 0 && (
              <div className="organizations-table-container">
                <table className="organizations-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Slug</th>
                      <th>Tier</th>
                      <th>Status</th>
                      <th>Users</th>
                      <th>Recipes</th>
                      <th>Distributors</th>
                      <th>AI Parses</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {organizations.map(org => (
                      <tr key={org.id}>
                        <td className="org-name">{org.name}</td>
                        <td className="org-slug">
                          <code>{org.slug}</code>
                        </td>
                        <td>
                          <span className={`tier-badge tier-${org.subscription_tier}`}>
                            {org.subscription_tier}
                          </span>
                        </td>
                        <td>
                          <span className={`status-badge status-${org.subscription_status}`}>
                            {org.subscription_status}
                          </span>
                        </td>
                        <td className="limit-cell">
                          <span className="limit-value">
                            {org.max_users === -1 ? '∞' : org.max_users}
                          </span>
                        </td>
                        <td className="limit-cell">
                          <span className="limit-value">
                            {org.max_recipes === -1 ? '∞' : org.max_recipes}
                          </span>
                        </td>
                        <td className="limit-cell">
                          <span className="limit-value">
                            {org.max_distributors === -1 ? '∞' : org.max_distributors}
                          </span>
                        </td>
                        <td className="limit-cell">
                          <span className="limit-value">
                            {org.ai_parses_used_this_month} / {org.max_ai_parses_per_month === -1 ? '∞' : org.max_ai_parses_per_month}
                          </span>
                        </td>
                        <td className="actions-cell">
                          <button
                            className="btn-icon btn-icon-edit"
                            title="Edit organization"
                            onClick={() => handleEditOrg(org)}
                          >
                            <Edit size={14} />
                          </button>
                          <button
                            className="btn-icon btn-icon-stats"
                            title="View stats"
                            onClick={() => handleViewStats(org)}
                          >
                            <BarChart3 size={14} />
                          </button>
                          <button
                            className="btn-icon btn-icon-delete"
                            title="Delete organization"
                            onClick={() => handleDeleteOrg(org)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={closeAllModals}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Organization</h2>
              <button className="modal-close" onClick={closeAllModals}>
                <X size={24} />
              </button>
            </div>
            <form onSubmit={handleSubmitCreate} className="modal-form">
              <div className="form-group">
                <label htmlFor="name">Organization Name *</label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className={formErrors.name ? 'error' : ''}
                  placeholder="My Restaurant"
                />
                {formErrors.name && <span className="error-message">{formErrors.name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="slug">Slug *</label>
                <input
                  type="text"
                  id="slug"
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase() })}
                  className={formErrors.slug ? 'error' : ''}
                  placeholder="my-restaurant"
                />
                <small>Lowercase letters, numbers, and hyphens only</small>
                {formErrors.slug && <span className="error-message">{formErrors.slug}</span>}
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="tier">Subscription Tier *</label>
                  <select
                    id="tier"
                    value={formData.subscription_tier}
                    onChange={(e) => setFormData({ ...formData, subscription_tier: e.target.value })}
                  >
                    <option value="free">Free</option>
                    <option value="basic">Basic</option>
                    <option value="pro">Pro</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="status">Status *</label>
                  <select
                    id="status"
                    value={formData.subscription_status}
                    onChange={(e) => setFormData({ ...formData, subscription_status: e.target.value })}
                  >
                    <option value="active">Active</option>
                    <option value="trialing">Trialing</option>
                    <option value="past_due">Past Due</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="email">Contact Email</label>
                <input
                  type="email"
                  id="email"
                  value={formData.contact_email}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  className={formErrors.contact_email ? 'error' : ''}
                  placeholder="contact@restaurant.com"
                />
                {formErrors.contact_email && <span className="error-message">{formErrors.contact_email}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="phone">Contact Phone</label>
                <input
                  type="tel"
                  id="phone"
                  value={formData.contact_phone}
                  onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <div className="tier-limits-info">
                <h3>Tier Limits</h3>
                <div className="limits-grid">
                  {formData.subscription_tier === 'free' && (
                    <>
                      <div className="limit-item">
                        <span className="limit-label">Max Users:</span>
                        <span className="limit-amount">2</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Recipes:</span>
                        <span className="limit-amount">5</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Distributors:</span>
                        <span className="limit-amount">1</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">AI Parses/Month:</span>
                        <span className="limit-amount">10</span>
                      </div>
                    </>
                  )}
                  {formData.subscription_tier === 'basic' && (
                    <>
                      <div className="limit-item">
                        <span className="limit-label">Max Users:</span>
                        <span className="limit-amount">5</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Recipes:</span>
                        <span className="limit-amount">50</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Distributors:</span>
                        <span className="limit-amount">3</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">AI Parses/Month:</span>
                        <span className="limit-amount">100</span>
                      </div>
                    </>
                  )}
                  {formData.subscription_tier === 'pro' && (
                    <>
                      <div className="limit-item">
                        <span className="limit-label">Max Users:</span>
                        <span className="limit-amount">15</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Recipes:</span>
                        <span className="limit-amount">Unlimited</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Distributors:</span>
                        <span className="limit-amount">Unlimited</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">AI Parses/Month:</span>
                        <span className="limit-amount">500</span>
                      </div>
                    </>
                  )}
                  {formData.subscription_tier === 'enterprise' && (
                    <>
                      <div className="limit-item">
                        <span className="limit-label">Max Users:</span>
                        <span className="limit-amount">Unlimited</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Recipes:</span>
                        <span className="limit-amount">Unlimited</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">Max Distributors:</span>
                        <span className="limit-amount">Unlimited</span>
                      </div>
                      <div className="limit-item">
                        <span className="limit-label">AI Parses/Month:</span>
                        <span className="limit-amount">Unlimited</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn" onClick={closeAllModals}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Create Organization'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Organization Modal */}
      {showEditModal && selectedOrg && (
        <div className="modal-overlay" onClick={closeAllModals}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Organization</h2>
              <button className="modal-close" onClick={closeAllModals}>
                <X size={24} />
              </button>
            </div>
            <form onSubmit={handleSubmitEdit} className="modal-form">
              <div className="form-group">
                <label htmlFor="edit-name">Organization Name *</label>
                <input
                  type="text"
                  id="edit-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className={formErrors.name ? 'error' : ''}
                />
                {formErrors.name && <span className="error-message">{formErrors.name}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-slug">Slug</label>
                <input
                  type="text"
                  id="edit-slug"
                  value={formData.slug}
                  disabled
                  className="disabled"
                />
                <small>Slug cannot be changed after creation</small>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="edit-tier">Subscription Tier *</label>
                  <select
                    id="edit-tier"
                    value={formData.subscription_tier}
                    onChange={(e) => setFormData({ ...formData, subscription_tier: e.target.value })}
                  >
                    <option value="free">Free</option>
                    <option value="basic">Basic</option>
                    <option value="pro">Pro</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="edit-status">Status *</label>
                  <select
                    id="edit-status"
                    value={formData.subscription_status}
                    onChange={(e) => setFormData({ ...formData, subscription_status: e.target.value })}
                  >
                    <option value="active">Active</option>
                    <option value="trialing">Trialing</option>
                    <option value="past_due">Past Due</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="edit-email">Contact Email</label>
                <input
                  type="email"
                  id="edit-email"
                  value={formData.contact_email}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  className={formErrors.contact_email ? 'error' : ''}
                />
                {formErrors.contact_email && <span className="error-message">{formErrors.contact_email}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="edit-phone">Contact Phone</label>
                <input
                  type="tel"
                  id="edit-phone"
                  value={formData.contact_phone}
                  onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn" onClick={closeAllModals}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Updating...' : 'Update Organization'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Stats Modal */}
      {showStatsModal && selectedOrg && (
        <div className="modal-overlay" onClick={closeAllModals}>
          <div className="modal-content modal-stats" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedOrg.name} - Statistics</h2>
              <button className="modal-close" onClick={closeAllModals}>
                <X size={24} />
              </button>
            </div>

            {loadingStats ? (
              <div className="loading-state">
                <div className="loading-spinner-enhanced"></div>
                <p>Loading statistics...</p>
              </div>
            ) : orgStats ? (
              <div className="stats-content">
                <div className="stats-header">
                  <div className="stats-meta">
                    <span className={`tier-badge tier-${orgStats.subscription_tier}`}>
                      {orgStats.subscription_tier}
                    </span>
                    <code className="org-slug-display">{selectedOrg.slug}</code>
                  </div>
                </div>

                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-icon">
                      <Users size={24} />
                    </div>
                    <div className="stat-details">
                      <h3>Users</h3>
                      <div className="stat-value">
                        {orgStats.users.current} / {orgStats.users.max === -1 ? '∞' : orgStats.users.max}
                      </div>
                      <div className="stat-progress">
                        <div
                          className="stat-progress-bar"
                          style={{
                            width: orgStats.users.max === -1 ? '0%' : `${(orgStats.users.current / orgStats.users.max) * 100}%`
                          }}
                        />
                      </div>
                      <div className="stat-footer">
                        {orgStats.users.available === -1 ? (
                          <span className="available unlimited">Unlimited available</span>
                        ) : (
                          <span className="available">{orgStats.users.available} available</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-icon">
                      <Building2 size={24} />
                    </div>
                    <div className="stat-details">
                      <h3>Recipes</h3>
                      <div className="stat-value">
                        {orgStats.recipes.current} / {orgStats.recipes.max === -1 ? '∞' : orgStats.recipes.max}
                      </div>
                      <div className="stat-progress">
                        <div
                          className="stat-progress-bar"
                          style={{
                            width: orgStats.recipes.max === -1 ? '0%' : `${(orgStats.recipes.current / orgStats.recipes.max) * 100}%`
                          }}
                        />
                      </div>
                      <div className="stat-footer">
                        {orgStats.recipes.available === -1 ? (
                          <span className="available unlimited">Unlimited available</span>
                        ) : (
                          <span className="available">{orgStats.recipes.available} available</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-icon">
                      <Building2 size={24} />
                    </div>
                    <div className="stat-details">
                      <h3>Distributors</h3>
                      <div className="stat-value">
                        {orgStats.distributors.current} / {orgStats.distributors.max === -1 ? '∞' : orgStats.distributors.max}
                      </div>
                      <div className="stat-progress">
                        <div
                          className="stat-progress-bar"
                          style={{
                            width: orgStats.distributors.max === -1 ? '0%' : `${(orgStats.distributors.current / orgStats.distributors.max) * 100}%`
                          }}
                        />
                      </div>
                      <div className="stat-footer">
                        {orgStats.distributors.available === -1 ? (
                          <span className="available unlimited">Unlimited available</span>
                        ) : (
                          <span className="available">{orgStats.distributors.available} available</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-icon">
                      <BarChart3 size={24} />
                    </div>
                    <div className="stat-details">
                      <h3>AI Parses This Month</h3>
                      <div className="stat-value">
                        {orgStats.ai_parses.used_this_month} / {orgStats.ai_parses.max === -1 ? '∞' : orgStats.ai_parses.max}
                      </div>
                      <div className="stat-progress">
                        <div
                          className="stat-progress-bar"
                          style={{
                            width: orgStats.ai_parses.max === -1 ? '0%' : `${(orgStats.ai_parses.used_this_month / orgStats.ai_parses.max) * 100}%`
                          }}
                        />
                      </div>
                      <div className="stat-footer">
                        {orgStats.ai_parses.available === -1 ? (
                          <span className="available unlimited">Unlimited available</span>
                        ) : (
                          <span className="available">{orgStats.ai_parses.available} available</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="error-state">
                <p>Failed to load statistics</p>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn" onClick={closeAllModals}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </>
  );
}

export default Admin;
