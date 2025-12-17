import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import axios from '../../lib/axios';
import './SuperAdmin.css';

export default function SuperAdminOrganizationDetail() {
  const { orgId } = useParams();
  const navigate = useNavigate();
  const [organization, setOrganization] = useState(null);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [showEditUserModal, setShowEditUserModal] = useState(false);
  const [showToggleUserModal, setShowToggleUserModal] = useState(false);
  const [showManageOutletsModal, setShowManageOutletsModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Form states
  const [editUserForm, setEditUserForm] = useState({
    full_name: '',
    role: 'admin',
    password: ''
  });
  const [selectedOutletIds, setSelectedOutletIds] = useState([]);

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

  const openEditUserModal = (user) => {
    setSelectedUser(user);
    setEditUserForm({
      full_name: user.full_name || '',
      role: user.role,
      password: ''
    });
    setShowEditUserModal(true);
  };

  const openToggleUserModal = (user) => {
    setSelectedUser(user);
    setShowToggleUserModal(true);
  };

  const openManageOutletsModal = (user) => {
    setSelectedUser(user);
    setSelectedOutletIds(user.assigned_outlet_ids || []);
    setShowManageOutletsModal(true);
  };

  const handleManageOutlets = async (e) => {
    e.preventDefault();
    try {
      await axios.patch(`/super-admin/users/${selectedUser.id}/outlets`, {
        outlet_ids: selectedOutletIds
      });
      alert('Outlet assignments updated successfully');
      setShowManageOutletsModal(false);
      setSelectedUser(null);
      fetchOrganizationDetail();
    } catch (error) {
      console.error('Error updating outlet assignments:', error);
      alert(error.response?.data?.detail || 'Error updating outlet assignments');
    }
  };

  const toggleOutletSelection = (outletId) => {
    setSelectedOutletIds(prev => {
      if (prev.includes(outletId)) {
        return prev.filter(id => id !== outletId);
      } else {
        return [...prev, outletId];
      }
    });
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    try {
      // Only include password if it's not empty
      const updateData = {
        full_name: editUserForm.full_name,
        role: editUserForm.role
      };
      if (editUserForm.password) {
        updateData.password = editUserForm.password;
      }

      await axios.patch(`/super-admin/users/${selectedUser.id}`, updateData);
      alert('User updated successfully');
      setShowEditUserModal(false);
      setSelectedUser(null);
      fetchOrganizationDetail();
    } catch (error) {
      console.error('Error updating user:', error);
      alert(error.response?.data?.detail || 'Error updating user');
    }
  };

  const handleToggleUserStatus = async () => {
    try {
      await axios.patch(`/super-admin/users/${selectedUser.id}`, {
        is_active: !selectedUser.is_active
      });
      alert(`User ${selectedUser.is_active ? 'deactivated' : 'activated'} successfully`);
      setShowToggleUserModal(false);
      setSelectedUser(null);
      fetchOrganizationDetail();
    } catch (error) {
      console.error('Error toggling user status:', error);
      alert(error.response?.data?.detail || 'Error updating user status');
    }
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
                <th>Outlets</th>
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
                    {user.role === 'admin' ? (
                      <span className="outlet-badge all-outlets">All Outlets</span>
                    ) : user.assigned_outlet_ids && user.assigned_outlet_ids.length > 0 ? (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {user.assigned_outlet_ids.map(outletId => {
                          const outlet = organization.outlets.find(o => o.id === outletId);
                          return outlet ? (
                            <span key={outletId} className="outlet-badge">
                              {outlet.name}
                            </span>
                          ) : null;
                        })}
                      </div>
                    ) : (
                      <span className="outlet-badge no-outlets">No Outlets</span>
                    )}
                  </td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <button className="action-btn" onClick={() => openEditUserModal(user)}>
                      Edit
                    </button>
                    {user.role !== 'admin' && (
                      <button className="action-btn" onClick={() => openManageOutletsModal(user)}>
                        Manage Outlets
                      </button>
                    )}
                    <button className="action-btn" onClick={() => openToggleUserModal(user)}>
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

      {/* Edit User Modal */}
      {showEditUserModal && selectedUser && (
        <div className="modal-overlay" onClick={() => setShowEditUserModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Edit User: {selectedUser.email}</h2>
            <form onSubmit={handleEditUser}>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={editUserForm.full_name}
                  onChange={(e) => setEditUserForm({...editUserForm, full_name: e.target.value})}
                  placeholder="John Doe"
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={editUserForm.role}
                  onChange={(e) => setEditUserForm({...editUserForm, role: e.target.value})}
                >
                  <option value="admin">Admin</option>
                  <option value="chef">Chef</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="form-group">
                <label>New Password (optional)</label>
                <input
                  type="text"
                  value={editUserForm.password}
                  onChange={(e) => setEditUserForm({...editUserForm, password: e.target.value})}
                  placeholder="Leave blank to keep current password"
                />
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowEditUserModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Update User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toggle User Status Modal */}
      {showToggleUserModal && selectedUser && (
        <div className="modal-overlay" onClick={() => setShowToggleUserModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{selectedUser.is_active ? 'Deactivate' : 'Activate'} User</h2>
            <p>
              Are you sure you want to {selectedUser.is_active ? 'deactivate' : 'activate'}{' '}
              <strong>{selectedUser.email}</strong>?
            </p>
            {selectedUser.is_active && (
              <p style={{ color: '#dc2626', marginTop: '1rem' }}>
                Warning: Deactivating this user will prevent them from accessing the system.
              </p>
            )}
            <div className="modal-actions">
              <button onClick={() => setShowToggleUserModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleToggleUserStatus}
                className="btn-primary"
                style={{
                  background: selectedUser.is_active ? '#dc2626' : '#52c41a',
                  borderColor: selectedUser.is_active ? '#dc2626' : '#52c41a'
                }}
              >
                {selectedUser.is_active ? 'Deactivate User' : 'Activate User'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manage Outlets Modal */}
      {showManageOutletsModal && selectedUser && (
        <div className="modal-overlay" onClick={() => setShowManageOutletsModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Manage Outlets: {selectedUser.email}</h2>
            <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
              Select which outlets this user can access. Admins always have access to all outlets.
            </p>
            <form onSubmit={handleManageOutlets}>
              <div className="form-group">
                {organization.outlets.length === 0 ? (
                  <p style={{ color: '#6b7280', fontStyle: 'italic' }}>
                    No outlets available. Create outlets first to assign them to users.
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {organization.outlets.map(outlet => (
                      <label
                        key={outlet.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          padding: '0.5rem',
                          border: '1px solid #e5e7eb',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          backgroundColor: selectedOutletIds.includes(outlet.id) ? '#f0f9ff' : 'white'
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedOutletIds.includes(outlet.id)}
                          onChange={() => toggleOutletSelection(outlet.id)}
                          style={{ cursor: 'pointer' }}
                        />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 500 }}>{outlet.name}</div>
                          {outlet.location && (
                            <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                              {outlet.location}
                            </div>
                          )}
                        </div>
                        <span className={`status-badge ${outlet.is_active ? 'active' : 'inactive'}`}>
                          {outlet.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowManageOutletsModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={organization.outlets.length === 0}>
                  Save Assignments
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
