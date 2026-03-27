import { useState, useEffect } from 'react';
import Navigation from '../../components/Navigation';
import { useToast } from '../../contexts/ToastContext';
import { useAuth } from '../../contexts/AuthContext';
import './EHC.css';

// API helper with auth
const API_BASE = '/api/ehc';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

async function fetchWithAuth(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers
    }
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

// Status badge component
function StatusBadge({ status }) {
  const statusConfig = {
    not_started: { label: 'Not Started', class: 'badge-neutral' },
    in_progress: { label: 'In Progress', class: 'badge-yellow' },
    evidence_collected: { label: 'Evidence Collected', class: 'badge-blue' },
    verified: { label: 'Verified', class: 'badge-green' },
    flagged: { label: 'Flagged', class: 'badge-red' },
    pending: { label: 'Pending', class: 'badge-neutral' },
    submitted: { label: 'Submitted', class: 'badge-yellow' },
    approved: { label: 'Approved', class: 'badge-green' },
    not_applicable: { label: 'N/A', class: 'badge-neutral' },
  };

  const config = statusConfig[status] || { label: status, class: 'badge-neutral' };

  return <span className={`status-badge ${config.class}`}>{config.label}</span>;
}

// NC Level badge component
function NCBadge({ level }) {
  const ncConfig = {
    1: { label: 'NC1', class: 'nc-critical', title: 'Critical - Food Safety Risk' },
    2: { label: 'NC2', class: 'nc-operational', title: 'Operational Compliance' },
    3: { label: 'NC3', class: 'nc-structural', title: 'Structural/Documentation' },
    4: { label: 'NC4', class: 'nc-admin', title: 'Administrative Records' },
  };

  const config = ncConfig[level] || { label: `NC${level}`, class: 'nc-admin' };

  return (
    <span className={`nc-badge ${config.class}`} title={config.title}>
      {config.label}
    </span>
  );
}

// Progress ring component
function ProgressRing({ percentage, size = 120, strokeWidth = 8 }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const getColor = (pct) => {
    if (pct >= 80) return 'var(--color-green)';
    if (pct >= 50) return 'var(--color-yellow)';
    return 'var(--color-red)';
  };

  return (
    <div className="progress-ring-container">
      <svg width={size} height={size} className="progress-ring">
        <circle
          className="progress-ring-bg"
          stroke="var(--border-subtle)"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          className="progress-ring-progress"
          stroke={getColor(percentage)}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          r={radius}
          cx={size / 2}
          cy={size / 2}
          style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
        />
      </svg>
      <div className="progress-ring-text">
        <span className="progress-ring-value">{Math.round(percentage)}%</span>
        <span className="progress-ring-label">Complete</span>
      </div>
    </div>
  );
}

// Section progress bar
function SectionProgress({ section }) {
  const pct = section.progress?.completion_pct || 0;

  return (
    <div className="section-progress">
      <div className="section-progress-header">
        <span className="section-number">{section.ref_number}</span>
        <span className="section-name">{section.name}</span>
        <span className="section-pct">{pct}%</span>
      </div>
      <div className="section-progress-bar">
        <div
          className="section-progress-fill"
          style={{
            width: `${pct}%`,
            backgroundColor: pct >= 80 ? 'var(--color-green)' : pct >= 50 ? 'var(--color-yellow)' : 'var(--color-red)'
          }}
        />
      </div>
      <div className="section-progress-stats">
        <span>{section.progress?.completed_points || 0} / {section.progress?.total_points || 0} points</span>
      </div>
    </div>
  );
}

// Main EHC Component
function EHC() {
  const { showToast } = useToast();
  const { user, isAdmin } = useAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [cycles, setCycles] = useState([]);
  const [activeCycle, setActiveCycle] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [points, setPoints] = useState([]);
  const [view, setView] = useState('dashboard'); // dashboard | points | records
  const [filters, setFilters] = useState({
    section: null,
    ncLevel: null,
    status: null,
  });
  const [expandedPoint, setExpandedPoint] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCycleYear, setNewCycleYear] = useState(new Date().getFullYear());

  // Load cycles on mount
  useEffect(() => {
    loadCycles();
  }, []);

  // Load dashboard when active cycle changes
  useEffect(() => {
    if (activeCycle) {
      loadDashboard(activeCycle.id);
    }
  }, [activeCycle]);

  // Load points when filters change or view switches to points
  useEffect(() => {
    if (activeCycle && view === 'points') {
      loadPoints(activeCycle.id);
    }
  }, [activeCycle, view, filters]);

  async function loadCycles() {
    try {
      setLoading(true);
      const data = await fetchWithAuth(`${API_BASE}/cycles`);
      setCycles(data.data || []);

      // Set active cycle to the most recent preparing/in_progress cycle
      const active = data.data?.find(c => c.status === 'preparing' || c.status === 'in_progress') || data.data?.[0];
      setActiveCycle(active || null);
    } catch (error) {
      showToast('Failed to load audit cycles', 'error');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  async function loadDashboard(cycleId) {
    try {
      const data = await fetchWithAuth(`${API_BASE}/cycles/${cycleId}/dashboard`);
      setDashboard(data);
    } catch (error) {
      showToast('Failed to load dashboard', 'error');
      console.error(error);
    }
  }

  async function loadPoints(cycleId) {
    try {
      let url = `${API_BASE}/cycles/${cycleId}/points?`;
      if (filters.section) url += `section=${filters.section}&`;
      if (filters.ncLevel) url += `nc_level=${filters.ncLevel}&`;
      if (filters.status) url += `status=${filters.status}&`;

      const data = await fetchWithAuth(url);
      setPoints(data.data || []);
    } catch (error) {
      showToast('Failed to load audit points', 'error');
      console.error(error);
    }
  }

  async function createCycle() {
    try {
      await fetchWithAuth(`${API_BASE}/cycles`, {
        method: 'POST',
        body: JSON.stringify({ year: newCycleYear })
      });
      showToast(`Audit cycle ${newCycleYear} created`, 'success');
      setShowCreateModal(false);
      loadCycles();
    } catch (error) {
      showToast(error.message || 'Failed to create cycle', 'error');
    }
  }

  async function updatePointStatus(pointId, status) {
    try {
      await fetchWithAuth(`${API_BASE}/points/${pointId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status })
      });
      showToast('Status updated', 'success');
      loadPoints(activeCycle.id);
      loadDashboard(activeCycle.id);
    } catch (error) {
      showToast('Failed to update status', 'error');
    }
  }

  // Render loading state
  if (loading) {
    return (
      <div className="ehc-page">
        <Navigation />
        <div className="ehc-container">
          <div className="loading-state">Loading EHC data...</div>
        </div>
      </div>
    );
  }

  // Render no cycles state
  if (cycles.length === 0) {
    return (
      <div className="ehc-page">
        <Navigation />
        <div className="ehc-header">
          <div className="header-content">
            <div className="header-title">
              <h1>EHC Audit Compliance</h1>
              <p>Environmental Health Compliance tracking and audit preparation</p>
            </div>
          </div>
        </div>
        <div className="ehc-container">
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h2>No Audit Cycles</h2>
            <p>Create your first audit cycle to start tracking EHC compliance.</p>
            {isAdmin() && (
              <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
                Create {new Date().getFullYear()} Cycle
              </button>
            )}
          </div>
        </div>

        {/* Create Modal */}
        {showCreateModal && (
          <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3>Create Audit Cycle</h3>
              <div className="form-group">
                <label>Year</label>
                <input
                  type="number"
                  value={newCycleYear}
                  onChange={e => setNewCycleYear(parseInt(e.target.value))}
                  min={2020}
                  max={2030}
                />
              </div>
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={createCycle}>
                  Create Cycle
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="ehc-page">
      <Navigation />

      {/* Header */}
      <div className="ehc-header">
        <div className="header-content">
          <div className="header-title">
            <h1>EHC Audit Compliance</h1>
            <p>
              {activeCycle?.name} - {activeCycle?.status}
              {dashboard?.days_until_audit !== null && dashboard?.days_until_audit !== undefined && (
                <span className="days-until">
                  {dashboard.days_until_audit > 0
                    ? ` (${dashboard.days_until_audit} days until audit)`
                    : dashboard.days_until_audit === 0
                      ? ' (Audit day!)'
                      : ` (${Math.abs(dashboard.days_until_audit)} days past audit)`
                  }
                </span>
              )}
            </p>
          </div>

          <div className="header-actions">
            {/* Cycle selector */}
            <select
              value={activeCycle?.id || ''}
              onChange={e => {
                const cycle = cycles.find(c => c.id === parseInt(e.target.value));
                setActiveCycle(cycle);
              }}
              className="cycle-selector"
            >
              {cycles.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>

            {/* View tabs */}
            <div className="view-tabs">
              <button
                className={`view-tab ${view === 'dashboard' ? 'active' : ''}`}
                onClick={() => setView('dashboard')}
              >
                Dashboard
              </button>
              <button
                className={`view-tab ${view === 'points' ? 'active' : ''}`}
                onClick={() => setView('points')}
              >
                Audit Points
              </button>
            </div>

            {isAdmin() && (
              <button className="btn-secondary" onClick={() => setShowCreateModal(true)}>
                + New Cycle
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="ehc-container">
        {/* Dashboard View */}
        {view === 'dashboard' && dashboard && (
          <div className="dashboard-view">
            {/* Top Stats Row */}
            <div className="stats-row">
              <div className="stat-card progress-card">
                <ProgressRing percentage={dashboard.overall_progress?.completion_pct || 0} />
                <div className="progress-details">
                  <div className="stat-label">Overall Readiness</div>
                  <div className="stat-breakdown">
                    <span>{dashboard.overall_progress?.completed_points || 0} verified</span>
                    <span className="stat-sep">/</span>
                    <span>{dashboard.overall_progress?.total_points || 0} total points</span>
                  </div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-value">{dashboard.submission_stats?.approved || 0}</div>
                <div className="stat-label">Records Approved</div>
                <div className="stat-subtext">
                  of {dashboard.submission_stats?.total || 0} submissions
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-value nc-critical">{dashboard.nc_breakdown?.find(n => n.nc_level === 1)?.completed || 0}</div>
                <div className="stat-label">NC1 Critical Complete</div>
                <div className="stat-subtext">
                  of {dashboard.nc_breakdown?.find(n => n.nc_level === 1)?.total || 0} critical points
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-value">{dashboard.overall_progress?.flagged || 0}</div>
                <div className="stat-label">Flagged Items</div>
                <div className="stat-subtext">require attention</div>
              </div>
            </div>

            {/* Sections Progress */}
            <div className="sections-card">
              <h3>Section Progress</h3>
              <div className="sections-grid">
                {dashboard.sections?.map(section => (
                  <SectionProgress key={section.id} section={section} />
                ))}
              </div>
            </div>

            {/* NC Level Breakdown */}
            <div className="nc-breakdown-card">
              <h3>Non-Conformance Level Breakdown</h3>
              <div className="nc-grid">
                {dashboard.nc_breakdown?.map(nc => (
                  <div key={nc.nc_level} className="nc-item">
                    <NCBadge level={nc.nc_level} />
                    <div className="nc-progress">
                      <div className="nc-progress-bar">
                        <div
                          className="nc-progress-fill"
                          style={{ width: `${nc.completion_pct}%` }}
                        />
                      </div>
                      <span className="nc-progress-text">
                        {nc.completed} / {nc.total} ({nc.completion_pct}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Points View */}
        {view === 'points' && (
          <div className="points-view">
            {/* Filters */}
            <div className="filters-bar">
              <select
                value={filters.section || ''}
                onChange={e => setFilters({ ...filters, section: e.target.value || null })}
              >
                <option value="">All Sections</option>
                {[1, 2, 3, 4, 5, 6].map(n => (
                  <option key={n} value={n}>Section {n}</option>
                ))}
              </select>

              <select
                value={filters.ncLevel || ''}
                onChange={e => setFilters({ ...filters, ncLevel: e.target.value || null })}
              >
                <option value="">All NC Levels</option>
                <option value="1">NC1 - Critical</option>
                <option value="2">NC2 - Operational</option>
                <option value="3">NC3 - Structural</option>
                <option value="4">NC4 - Administrative</option>
              </select>

              <select
                value={filters.status || ''}
                onChange={e => setFilters({ ...filters, status: e.target.value || null })}
              >
                <option value="">All Statuses</option>
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="evidence_collected">Evidence Collected</option>
                <option value="verified">Verified</option>
                <option value="flagged">Flagged</option>
              </select>

              {(filters.section || filters.ncLevel || filters.status) && (
                <button
                  className="btn-ghost"
                  onClick={() => setFilters({ section: null, ncLevel: null, status: null })}
                >
                  Clear Filters
                </button>
              )}

              <span className="filter-count">{points.length} points</span>
            </div>

            {/* Points Table */}
            <div className="points-table-container">
              <table className="points-table">
                <thead>
                  <tr>
                    <th>Ref</th>
                    <th>Question</th>
                    <th>NC</th>
                    <th>Status</th>
                    <th>Area</th>
                    <th>Records</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map(point => (
                    <>
                      <tr
                        key={point.id}
                        className={`point-row ${expandedPoint === point.id ? 'expanded' : ''}`}
                        onClick={() => setExpandedPoint(expandedPoint === point.id ? null : point.id)}
                      >
                        <td className="point-ref">{point.ref_code}</td>
                        <td className="point-question">{point.question_text}</td>
                        <td><NCBadge level={point.nc_level} /></td>
                        <td><StatusBadge status={point.status} /></td>
                        <td className="point-area">{point.responsible_area || '-'}</td>
                        <td className="point-records">
                          {point.linked_record_count > 0 ? (
                            <span className="record-count">{point.linked_record_count}</span>
                          ) : (
                            <span className="no-records">Obs</span>
                          )}
                        </td>
                        <td className="point-actions" onClick={e => e.stopPropagation()}>
                          <select
                            value={point.status}
                            onChange={e => updatePointStatus(point.id, e.target.value)}
                            className="status-select"
                          >
                            <option value="not_started">Not Started</option>
                            <option value="in_progress">In Progress</option>
                            <option value="evidence_collected">Evidence Collected</option>
                            <option value="verified">Verified</option>
                            <option value="flagged">Flagged</option>
                          </select>
                        </td>
                      </tr>
                      {expandedPoint === point.id && (
                        <tr className="point-expanded-row">
                          <td colSpan="7">
                            <div className="point-details">
                              <div className="point-detail-section">
                                <strong>Section:</strong> {point.section_name}
                              </div>
                              <div className="point-detail-section">
                                <strong>Subsection:</strong> {point.subsection_code} - {point.subsection_name}
                              </div>
                              <div className="point-detail-section">
                                <strong>Max Score:</strong> {point.max_score} pts
                              </div>
                              {point.notes && (
                                <div className="point-detail-section">
                                  <strong>Notes:</strong> {point.notes}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>

              {points.length === 0 && (
                <div className="no-results">
                  No audit points match your filters.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Create Cycle Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Create Audit Cycle</h3>
            <p className="modal-description">
              This will create a new EHC audit cycle and seed all 125 audit points,
              47 records, and generate submission periods for the year.
            </p>
            <div className="form-group">
              <label>Year</label>
              <input
                type="number"
                value={newCycleYear}
                onChange={e => setNewCycleYear(parseInt(e.target.value))}
                min={2020}
                max={2030}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={createCycle}>
                Create Cycle
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EHC;
