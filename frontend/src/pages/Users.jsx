import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from '../lib/axios';
import { useAuth } from '../context/AuthContext';
import './Users.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

function Users() {
  const { user, getAuthHeader, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
    role: 'viewer'
  });

  useEffect(() => {
    if (!isAdmin()) {
      navigate('/');
      return;
    }
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/auth/users`, {
        headers: getAuthHeader()
      });
      setUsers(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching users:', err);
      setError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await axios.patch(
        `${API_URL}/auth/users/${userId}`,
        { role: newRole },
        { headers: getAuthHeader() }
      );
      setUsers(users.map(u =>
        u.id === userId ? { ...u, role: newRole } : u
      ));
      setEditingUser(null);
    } catch (err) {
      console.error('Error updating role:', err);
      setError('Failed to update user role');
    }
  };

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await axios.patch(
        `${API_URL}/auth/users/${userId}`,
        { is_active: !currentStatus },
        { headers: getAuthHeader() }
      );
      setUsers(users.map(u =>
        u.id === userId ? { ...u, is_active: !currentStatus } : u
      ));
    } catch (err) {
      console.error('Error updating status:', err);
      setError('Failed to update user status');
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(
        `${API_URL}/auth/register`,
        newUser,
        { headers: getAuthHeader() }
      );
      setUsers([...users, response.data]);
      setShowAddModal(false);
      setNewUser({
        email: '',
        username: '',
        password: '',
        full_name: '',
        role: 'viewer'
      });
    } catch (err) {
      console.error('Error adding user:', err);
      setError(err.response?.data?.detail || 'Failed to add user');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="users-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="users-page">
      <header className="users-header">
        <div className="header-left">
          <Link to="/" className="back-link">← Back to Home</Link>
          <h1>User Management</h1>
        </div>
        <div className="header-right">
          <div className="user-info">
            <span className="user-name">{user?.full_name || user?.username}</span>
            <span className={`user-role role-${user?.role}`}>{user?.role}</span>
          </div>
          <button className="btn-logout" onClick={handleLogout}>Sign Out</button>
        </div>
      </header>

      <main className="users-content">
        <div className="users-toolbar">
          <div className="users-count">
            {users.length} user{users.length !== 1 ? 's' : ''}
          </div>
          <button className="btn-add-user" onClick={() => setShowAddModal(true)}>
            + Add User
          </button>
        </div>

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        <div className="users-table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className={!u.is_active ? 'inactive-user' : ''}>
                  <td>
                    <div className="user-cell">
                      <span className="username">{u.username}</span>
                      {u.full_name && <span className="fullname">{u.full_name}</span>}
                    </div>
                  </td>
                  <td>{u.email}</td>
                  <td>
                    {editingUser === u.id ? (
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        onBlur={() => setEditingUser(null)}
                        autoFocus
                        className="role-select"
                      >
                        <option value="admin">Admin</option>
                        <option value="chef">Chef</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    ) : (
                      <span
                        className={`role-badge role-${u.role}`}
                        onClick={() => u.id !== user.id && setEditingUser(u.id)}
                        title={u.id === user.id ? "Can't change your own role" : "Click to change role"}
                      >
                        {u.role}
                      </span>
                    )}
                  </td>
                  <td>
                    <span className={`status-badge ${u.is_active ? 'active' : 'inactive'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    {u.id !== user.id && (
                      <button
                        className={`btn-toggle ${u.is_active ? 'deactivate' : 'activate'}`}
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add New User</h2>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddUser}>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={e => setNewUser({...newUser, email: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={e => setNewUser({...newUser, username: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={e => setNewUser({...newUser, password: e.target.value})}
                  required
                  minLength={6}
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={e => setNewUser({...newUser, full_name: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={newUser.role}
                  onChange={e => setNewUser({...newUser, role: e.target.value})}
                >
                  <option value="viewer">Viewer</option>
                  <option value="chef">Chef</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  Add User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;
