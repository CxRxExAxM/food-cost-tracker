import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import axios from '../../lib/axios';
import { useAuth } from '../../context/AuthContext';
import './SuperAdmin.css';

export default function SuperAdminOrganizations() {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  const { setToken } = useAuth();

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditTierModal, setShowEditTierModal] = useState(false);
  const [showSuspendModal, setShowSuspendModal] = useState(false);
  const [showCreateUserModal, setShowCreateUserModal] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState(null);

  // Form states
  const [createForm, setCreateForm] = useState({
    name: '',
    slug: '',
    subscription_tier: 'free'
  });
  const [editTier, setEditTier] = useState('');
  const [createUserForm, setCreateUserForm] = useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
    role: 'admin'
  });

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
      alert('Error loading organizations');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrg = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/super-admin/organizations', createForm);
      alert('Organization created successfully');
      setShowCreateModal(false);
      setCreateForm({ name: '', slug: '', subscription_tier: 'free' });
      fetchOrganizations();
    } catch (error) {
      console.error('Error creating organization:', error);
      alert(error.response?.data?.detail || 'Error creating organization');
    }
  };

  const handleEditTier = async (e) => {
    e.preventDefault();
    try {
      await axios.patch(`/super-admin/organizations/${selectedOrg.id}`, {
        subscription_tier: editTier
      });
      alert('Tier updated successfully');
      setShowEditTierModal(false);
      setSelectedOrg(null);
      fetchOrganizations();
    } catch (error) {
      console.error('Error updating tier:', error);
      alert(error.response?.data?.detail || 'Error updating tier');
    }
  };

  const handleSuspendToggle = async () => {
    try {
      const newStatus = selectedOrg.subscription_status === 'active' ? 'suspended' : 'active';
      await axios.patch(`/super-admin/organizations/${selectedOrg.id}`, {
        subscription_status: newStatus
      });
      alert(`Organization ${newStatus === 'active' ? 'activated' : 'suspended'} successfully`);
      setShowSuspendModal(false);
      setSelectedOrg(null);
      fetchOrganizations();
    } catch (error) {
      console.error('Error toggling status:', error);
      alert(error.response?.data?.detail || 'Error updating status');
    }
  };

  const openCreateModal = () => {
    setCreateForm({ name: '', slug: '', subscription_tier: 'free' });
    setShowCreateModal(true);
  };

  const openEditTierModal = (org) => {
    setSelectedOrg(org);
    setEditTier(org.subscription_tier);
    setShowEditTierModal(true);
  };

  const openSuspendModal = (org) => {
    setSelectedOrg(org);
    setShowSuspendModal(true);
  };

  const openCreateUserModal = (org) => {
    setSelectedOrg(org);
    setCreateUserForm({
      email: '',
      username: '',
      password: '',
      full_name: '',
      role: 'admin'
    });
    setShowCreateUserModal(true);
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`/super-admin/organizations/${selectedOrg.id}/users`, createUserForm);
      alert(`User created successfully!\n\nEmail: ${createUserForm.email}\nPassword: ${createUserForm.password}\n\nPlease save these credentials.`);
      setShowCreateUserModal(false);
      setSelectedOrg(null);
      fetchOrganizations();
    } catch (error) {
      console.error('Error creating user:', error);
      alert(error.response?.data?.detail || 'Error creating user');
    }
  };

  const handleImpersonate = async (org) => {
    try {
      const response = await axios.post(`/super-admin/impersonate/${org.id}`);
      // Use the setToken function from AuthContext to set the new token
      await setToken(response.data.access_token);
      // Navigate to home page in impersonated context
      navigate('/');
    } catch (error) {
      console.error('Error impersonating organization:', error);
      alert(error.response?.data?.detail || 'Error impersonating organization');
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
      <div className="super-admin-nav">
        <div className="super-admin-tabs">
          <Link
            to="/settings/super-admin"
            className={`super-admin-tab ${location.pathname === '/settings/super-admin' ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link
            to="/settings/super-admin/organizations"
            className={`super-admin-tab ${location.pathname.includes('/settings/super-admin/organizations') ? 'active' : ''}`}
          >
            Organizations
          </Link>
          <Link
            to="/settings/super-admin/audit-logs"
            className={`super-admin-tab ${location.pathname === '/settings/super-admin/audit-logs' ? 'active' : ''}`}
          >
            Audit Logs
          </Link>
        </div>
        <Link to="/" className="return-to-main-btn">
          ← Return to Main Site
        </Link>
      </div>

      <div className="organizations-header">
        <div>
          <h1>Organizations</h1>
          <p className="subtitle">Manage all platform organizations</p>
        </div>
        <button className="create-org-btn" onClick={openCreateModal}>
          + Create Organization
        </button>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="Search organizations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
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
                <Link to={`/super-admin/organizations/${org.id}`} className="org-name-link">
                  <h3>{org.name}</h3>
                </Link>
                <div className="org-slug">{org.slug}</div>
              </div>
              <div
                className="org-tier"
                style={{ backgroundColor: getTierColor(org.subscription_tier) }}
              >
                {org.subscription_tier}
              </div>
            </div>

            {org.subscription_status === 'suspended' && (
              <div style={{
                background: 'rgba(220, 38, 38, 0.1)',
                border: '1px solid #dc2626',
                borderRadius: '4px',
                padding: '0.5rem',
                marginTop: '0.5rem',
                color: '#ff4d4f',
                fontSize: '0.875rem',
                fontWeight: 600,
                textAlign: 'center'
              }}>
                SUSPENDED
              </div>
            )}

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
              <button
                onClick={() => handleImpersonate(org)}
                style={{ color: '#fadb14', fontWeight: 600 }}
              >
                Login as Admin
              </button>
              <button
                onClick={() => openCreateUserModal(org)}
                style={{ color: '#52c41a', fontWeight: 600 }}
              >
                + Create User
              </button>
              <button onClick={() => openEditTierModal(org)}>Edit Tier</button>
              <button
                onClick={() => openSuspendModal(org)}
                style={{ color: org.subscription_status === 'active' ? '#dc2626' : '#52c41a' }}
              >
                {org.subscription_status === 'active' ? 'Suspend' : 'Activate'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {organizations.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#6b7280' }}>
          No organizations found
        </div>
      )}

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create New Organization</h2>
            <form onSubmit={handleCreateOrg}>
              <div className="form-group">
                <label>Organization Name</label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({...createForm, name: e.target.value})}
                  required
                  placeholder="Acme Corporation"
                />
              </div>
              <div className="form-group">
                <label>Slug (URL-safe identifier)</label>
                <input
                  type="text"
                  value={createForm.slug}
                  onChange={(e) => setCreateForm({...createForm, slug: e.target.value})}
                  required
                  placeholder="acme_corp"
                  pattern="[a-z0-9_-]+"
                  title="Only lowercase letters, numbers, underscores, and hyphens"
                />
              </div>
              <div className="form-group">
                <label>Subscription Tier</label>
                <select
                  value={createForm.subscription_tier}
                  onChange={(e) => setCreateForm({...createForm, subscription_tier: e.target.value})}
                >
                  <option value="free">Free</option>
                  <option value="basic">Basic</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Organization
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Tier Modal */}
      {showEditTierModal && selectedOrg && (
        <div className="modal-overlay" onClick={() => setShowEditTierModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Edit Tier: {selectedOrg.name}</h2>
            <form onSubmit={handleEditTier}>
              <div className="form-group">
                <label>Subscription Tier</label>
                <select
                  value={editTier}
                  onChange={(e) => setEditTier(e.target.value)}
                  required
                >
                  <option value="free">Free</option>
                  <option value="basic">Basic</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowEditTierModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Update Tier
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Suspend/Activate Modal */}
      {showSuspendModal && selectedOrg && (
        <div className="modal-overlay" onClick={() => setShowSuspendModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>
              {selectedOrg.subscription_status === 'active' ? 'Suspend' : 'Activate'} Organization
            </h2>
            <p>
              Are you sure you want to {selectedOrg.subscription_status === 'active' ? 'suspend' : 'activate'} <strong>{selectedOrg.name}</strong>?
            </p>
            {selectedOrg.subscription_status === 'active' && (
              <p style={{ color: '#dc2626', marginTop: '1rem' }}>
                Warning: Suspending will prevent all users from accessing this organization.
              </p>
            )}
            <div className="modal-actions">
              <button onClick={() => setShowSuspendModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleSuspendToggle}
                className="btn-danger"
                style={{
                  background: selectedOrg.subscription_status === 'active' ? '#dc2626' : '#52c41a',
                  color: 'white'
                }}
              >
                {selectedOrg.subscription_status === 'active' ? 'Suspend Organization' : 'Activate Organization'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateUserModal && selectedOrg && (
        <div className="modal-overlay" onClick={() => setShowCreateUserModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create User for {selectedOrg.name}</h2>
            <form onSubmit={handleCreateUser}>
              <div className="form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={createUserForm.email}
                  onChange={(e) => setCreateUserForm({...createUserForm, email: e.target.value})}
                  required
                  placeholder="user@example.com"
                />
              </div>
              <div className="form-group">
                <label>Username *</label>
                <input
                  type="text"
                  value={createUserForm.username}
                  onChange={(e) => setCreateUserForm({...createUserForm, username: e.target.value})}
                  required
                  placeholder="username"
                />
              </div>
              <div className="form-group">
                <label>Password *</label>
                <input
                  type="text"
                  value={createUserForm.password}
                  onChange={(e) => setCreateUserForm({...createUserForm, password: e.target.value})}
                  required
                  placeholder="Enter password (will be shown to super admin)"
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={createUserForm.full_name}
                  onChange={(e) => setCreateUserForm({...createUserForm, full_name: e.target.value})}
                  placeholder="John Doe"
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={createUserForm.role}
                  onChange={(e) => setCreateUserForm({...createUserForm, role: e.target.value})}
                >
                  <option value="admin">Admin</option>
                  <option value="chef">Chef</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowCreateUserModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
