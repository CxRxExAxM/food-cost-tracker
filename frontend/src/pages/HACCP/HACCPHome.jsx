import { Link } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import { mockStats, mockInstances } from './mockData';
import './HACCP.css';

function HACCPHome() {
  const stats = mockStats;
  const pendingInstances = mockInstances.filter(i => i.status === 'pending');

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="haccp-container">
        <header className="haccp-header">
          <h1>HACCP Compliance Dashboard</h1>
          <p>Manage food safety checklists and temperature monitoring</p>
        </header>

        {/* Stats Cards */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">📋</div>
            <div className="stat-content">
              <div className="stat-value">{stats.totalChecklists}</div>
              <div className="stat-label">Checklists</div>
            </div>
            <Link to="/haccp/checklists" className="stat-action">
              Manage →
            </Link>
          </div>

          <div className="stat-card">
            <div className="stat-icon">📌</div>
            <div className="stat-content">
              <div className="stat-value">{stats.activeAssignments}</div>
              <div className="stat-label">Active Assignments</div>
            </div>
            <Link to="/haccp/assignments" className="stat-action">
              View →
            </Link>
          </div>

          <div className="stat-card stat-warning">
            <div className="stat-icon">⏰</div>
            <div className="stat-content">
              <div className="stat-value">{stats.dueToday}</div>
              <div className="stat-label">Due Today</div>
            </div>
            <div className="stat-action">
              {stats.dueToday > 0 ? 'Action Required' : 'All Clear'}
            </div>
          </div>

          <div className="stat-card stat-success">
            <div className="stat-icon">✓</div>
            <div className="stat-content">
              <div className="stat-value">{stats.completedThisWeek}</div>
              <div className="stat-label">Completed This Week</div>
            </div>
            <Link to="/haccp/reports" className="stat-action">
              View Reports →
            </Link>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="quick-actions">
          <h2>Quick Actions</h2>
          <div className="action-buttons">
            <Link to="/haccp/checklists/new" className="btn btn-primary">
              <span className="btn-icon">+</span>
              Create New Checklist
            </Link>
            <Link to="/haccp/assignments" className="btn btn-secondary">
              <span className="btn-icon">📌</span>
              Assign Checklist
            </Link>
          </div>
        </div>

        {/* Due Today List */}
        {pendingInstances.length > 0 && (
          <div className="due-today-section">
            <h2>Due Today</h2>
            <div className="checklist-list">
              {pendingInstances.map(instance => (
                <div key={instance.id} className="checklist-item">
                  <div className="checklist-info">
                    <h3>{instance.checklist_name}</h3>
                    <p>{instance.outlet_name}</p>
                    <div className="assigned-to">
                      Assigned to: {instance.assigned_to.join(', ')}
                    </div>
                  </div>
                  <Link
                    to={`/haccp/complete/${instance.id}`}
                    className="btn btn-small btn-primary"
                  >
                    Complete Checklist
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default HACCPHome;
