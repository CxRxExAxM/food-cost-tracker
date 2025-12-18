import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from '../../lib/axios';
import './SuperAdmin.css';

export default function SuperAdminAuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [organizations, setOrganizations] = useState([]);
  const [organizationFilter, setOrganizationFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    fetchAuditLogs();
  }, [organizationFilter, actionFilter]);

  const fetchOrganizations = async () => {
    try {
      const response = await axios.get('/super-admin/organizations');
      setOrganizations(response.data);
    } catch (error) {
      console.error('Error fetching organizations:', error);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = {};
      if (organizationFilter) params.organization_id = organizationFilter;
      if (actionFilter) params.action = actionFilter;

      const response = await axios.get('/super-admin/audit-logs', { params });
      setLogs(response.data);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const getActionBadgeColor = (action) => {
    if (action.includes('created')) return '#52c41a';
    if (action.includes('updated') || action.includes('changed')) return '#3b82f6';
    if (action.includes('deleted') || action.includes('deactivated') || action.includes('suspended')) return '#dc2626';
    if (action.includes('impersonation')) return '#f59e0b';
    return '#6b7280';
  };

  const formatChanges = (changes) => {
    if (!changes || typeof changes !== 'object') return '-';

    return Object.keys(changes).map((key, idx) => {
      const change = changes[key];
      if (typeof change === 'object' && change.from !== undefined && change.to !== undefined) {
        return (
          <div key={idx} className="change-item">
            <strong>{key}:</strong> {change.from} → {change.to}
          </div>
        );
      } else {
        return (
          <div key={idx} className="change-item">
            <strong>{key}:</strong> {JSON.stringify(change)}
          </div>
        );
      }
    });
  };

  if (loading) {
    return <div className="loading">Loading audit logs...</div>;
  }

  return (
    <div className="super-admin-audit-logs">
      <div className="super-admin-nav">
        <div className="super-admin-tabs">
          <Link to="/super-admin" className="super-admin-tab">
            Dashboard
          </Link>
          <Link to="/super-admin/organizations" className="super-admin-tab">
            Organizations
          </Link>
          <Link to="/super-admin/audit-logs" className="super-admin-tab active">
            Audit Logs
          </Link>
        </div>
        <Link to="/" className="return-to-main-btn">
          ← Return to Main App
        </Link>
      </div>

      <h1>Audit Logs</h1>
      <p className="subtitle">Platform-wide activity tracking</p>

      {/* Filters */}
      <div className="filters-section">
        <div className="filter-group">
          <label>Organization</label>
          <select
            value={organizationFilter}
            onChange={(e) => setOrganizationFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Organizations</option>
            {organizations.map(org => (
              <option key={org.id} value={org.id}>{org.name}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Action</label>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Actions</option>
            <option value="user_created">User Created</option>
            <option value="user_updated">User Updated</option>
            <option value="subscription_updated">Subscription Updated</option>
            <option value="impersonation_started">Impersonation Started</option>
            <option value="impersonation_ended">Impersonation Ended</option>
            <option value="outlet_assignments_updated">Outlet Assignments Updated</option>
          </select>
        </div>
        <button className="btn-clear-filters" onClick={() => { setOrganizationFilter(''); setActionFilter(''); }}>
          Clear Filters
        </button>
      </div>

      {/* Audit Logs Table */}
      <div className="audit-logs-container">
        {logs.length === 0 ? (
          <div className="empty-state">No audit logs found</div>
        ) : (
          <table className="audit-logs-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>User</th>
                <th>Organization</th>
                <th>Entity</th>
                <th>Changes</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className={log.impersonating ? 'impersonation-row' : ''}>
                  <td className="timestamp-cell">{formatDate(log.created_at)}</td>
                  <td>
                    <span
                      className="action-badge"
                      style={{ backgroundColor: getActionBadgeColor(log.action) }}
                    >
                      {log.action}
                    </span>
                    {log.impersonating && <span className="impersonation-indicator">👤</span>}
                  </td>
                  <td className="user-cell">
                    {log.user_email || '-'}
                    {log.impersonating && (
                      <div className="impersonation-note">via impersonation</div>
                    )}
                  </td>
                  <td>{log.organization_name || '-'}</td>
                  <td>
                    {log.entity_type && log.entity_id ? (
                      <span className="entity-info">
                        {log.entity_type} #{log.entity_id}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="changes-cell">{formatChanges(log.changes)}</td>
                  <td className="ip-cell">{log.ip_address || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
