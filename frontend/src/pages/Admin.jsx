import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Building2, Users, Save, BarChart3, AlertCircle, CheckCircle } from 'lucide-react';
import Navigation from '../components/Navigation';
import axios from '../lib/axios';
import './Admin.css';

function Admin({ embedded = false }) {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const [organization, setOrganization] = useState(null);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    contact_email: '',
    contact_phone: ''
  });
  const [saving, setSaving] = useState(false);

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
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchOrganization(),
        fetchStats(),
        fetchUsers()
      ]);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrganization = async () => {
    const response = await axios.get('/organizations/me');
    const data = response.data;
    setOrganization(data);
    setFormData({
      name: data.name || '',
      contact_email: data.contact_email || '',
      contact_phone: data.contact_phone || ''
    });
  };

  const fetchStats = async () => {
    const response = await axios.get('/organizations/me/stats');
    setStats(response.data);
  };

  const fetchUsers = async () => {
    const response = await axios.get('/auth/users');
    setUsers(response.data);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMessage('');

    try {
      const response = await axios.patch('/organizations/me', formData);
      const updatedOrg = response.data;
      setOrganization(updatedOrg);
      setSuccessMessage('Organization settings updated successfully!');

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update organization');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const getTierColor = (tier) => {
    const colors = {
      free: '#6B7280',
      basic: '#3B82F6',
      pro: '#10B981',
      enterprise: '#8B5CF6'
    };
    return colors[tier] || colors.free;
  };

  const getTierDisplayName = (tier) => {
    return tier.charAt(0).toUpperCase() + tier.slice(1);
  };

  const getUsageColor = (current, max) => {
    if (max === -1) return '#10B981'; // Unlimited - green
    const percentage = (current / max) * 100;
    if (percentage >= 90) return '#EF4444'; // Red
    if (percentage >= 75) return '#F59E0B'; // Yellow
    return '#10B981'; // Green
  };

  if (loading) {
    return (
      <div className="page-container">
        <Navigation onLogout={handleLogout} />
        <div className="admin-loading">Loading organization settings...</div>
      </div>
    );
  }

  return (
    <div className={`page-container ${embedded ? 'embedded' : ''}`}>
      {!embedded && <Navigation onLogout={handleLogout} />}

      <div className="admin-container">
        <div className="admin-header">
          <div className="admin-header-content">
            <Building2 size={32} />
            <h1>Organization Settings</h1>
          </div>
        </div>

        {error && (
          <div className="admin-alert admin-alert-error">
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        {successMessage && (
          <div className="admin-alert admin-alert-success">
            <CheckCircle size={20} />
            {successMessage}
          </div>
        )}

        <div className="admin-grid">
          {/* Organization Info Card */}
          <div className="admin-card">
            <div className="admin-card-header">
              <Building2 size={24} />
              <h2>Organization Information</h2>
            </div>

            <form onSubmit={handleSubmit} className="admin-form">
              <div className="admin-form-group">
                <label htmlFor="name">Organization Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="admin-input"
                />
              </div>

              <div className="admin-form-group">
                <label htmlFor="contact_email">Contact Email</label>
                <input
                  type="email"
                  id="contact_email"
                  name="contact_email"
                  value={formData.contact_email}
                  onChange={handleInputChange}
                  className="admin-input"
                  placeholder="contact@example.com"
                />
              </div>

              <div className="admin-form-group">
                <label htmlFor="contact_phone">Contact Phone</label>
                <input
                  type="tel"
                  id="contact_phone"
                  name="contact_phone"
                  value={formData.contact_phone}
                  onChange={handleInputChange}
                  className="admin-input"
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <div className="admin-tier-badge" style={{ backgroundColor: getTierColor(organization?.subscription_tier) }}>
                {getTierDisplayName(organization?.subscription_tier || 'free')} Plan
              </div>

              <button type="submit" className="admin-btn admin-btn-primary" disabled={saving}>
                <Save size={20} />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          {/* Usage Statistics Card */}
          {stats && stats.users && stats.recipes && stats.products && (
            <div className="admin-card">
              <div className="admin-card-header">
                <BarChart3 size={24} />
                <h2>Usage & Limits</h2>
              </div>

              <div className="admin-stats-grid">
                <div className="admin-stat-item">
                  <div className="admin-stat-label">
                    <Users size={18} />
                    Users
                  </div>
                  <div className="admin-stat-value">
                    <span style={{ color: getUsageColor(stats.users.current, stats.users.max) }}>
                      {stats.users.current}
                    </span>
                    <span className="admin-stat-max">
                      / {stats.users.max === -1 ? '∞' : stats.users.max}
                    </span>
                  </div>
                  {stats.users.max > 0 && (
                    <div className="admin-progress-bar">
                      <div
                        className="admin-progress-fill"
                        style={{
                          width: `${(stats.users.current / stats.users.max) * 100}%`,
                          backgroundColor: getUsageColor(stats.users.current, stats.users.max)
                        }}
                      />
                    </div>
                  )}
                </div>

                <div className="admin-stat-item">
                  <div className="admin-stat-label">
                    <BarChart3 size={18} />
                    Recipes
                  </div>
                  <div className="admin-stat-value">
                    <span style={{ color: getUsageColor(stats.recipes.current, stats.recipes.max) }}>
                      {stats.recipes.current}
                    </span>
                    <span className="admin-stat-max">
                      / {stats.recipes.max === -1 ? '∞' : stats.recipes.max}
                    </span>
                  </div>
                  {stats.recipes.max > 0 && (
                    <div className="admin-progress-bar">
                      <div
                        className="admin-progress-fill"
                        style={{
                          width: `${(stats.recipes.current / stats.recipes.max) * 100}%`,
                          backgroundColor: getUsageColor(stats.recipes.current, stats.recipes.max)
                        }}
                      />
                    </div>
                  )}
                </div>

                <div className="admin-stat-item">
                  <div className="admin-stat-label">
                    <Building2 size={18} />
                    Products
                  </div>
                  <div className="admin-stat-value">
                    <span style={{ color: '#10B981' }}>
                      {stats.products.current}
                    </span>
                    <span className="admin-stat-max">
                      / ∞
                    </span>
                  </div>
                </div>
              </div>

              {(stats.users.max > 0 && stats.users.current >= stats.users.max * 0.9) && (
                <div className="admin-warning">
                  <AlertCircle size={16} />
                  You're approaching your user limit. Consider upgrading your plan.
                </div>
              )}

              {(stats.recipes.max > 0 && stats.recipes.current >= stats.recipes.max * 0.9) && (
                <div className="admin-warning">
                  <AlertCircle size={16} />
                  You're approaching your recipe limit. Consider upgrading your plan.
                </div>
              )}
            </div>
          )}

          {/* Users List Card */}
          <div className="admin-card admin-users-card">
            <div className="admin-card-header">
              <Users size={24} />
              <h2>Team Members</h2>
            </div>

            <div className="admin-users-list">
              {users.map((u) => (
                <div key={u.id} className="admin-user-item">
                  <div className="admin-user-info">
                    <div className="admin-user-name">{u.full_name || u.username}</div>
                    <div className="admin-user-email">{u.email}</div>
                  </div>
                  <div className="admin-user-role-badge" data-role={u.role}>
                    {u.role}
                  </div>
                </div>
              ))}
            </div>

            <div className="admin-card-footer">
              <button
                className="admin-btn admin-btn-secondary"
                onClick={() => navigate('/users')}
              >
                Manage Users
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Admin;
