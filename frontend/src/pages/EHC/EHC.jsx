/**
 * EHC Module - Main Container
 *
 * Environmental Health Compliance module with 5-tab navigation:
 * - Dashboard: Overview stats, progress rings, section progress
 * - Audit Points: 125+ points with status tracking
 * - Records: Submission management with file uploads
 * - Forms: Digital form administration (coming soon)
 * - Settings: Module configuration (coming soon)
 */

import { useState, useEffect } from 'react';
import Navigation from '../../components/Navigation';
import { useToast } from '../../contexts/ToastContext';
import { useAuth } from '../../contexts/AuthContext';
import FormLinkModal from './FormLinkModal';
import ResponseTrackerModal from './ResponseTrackerModal';
import './EHC.css';

// Tab components
import Dashboard from './tabs/Dashboard';
import AuditPoints from './tabs/AuditPoints';
import Records from './tabs/Records';
import Forms from './tabs/Forms';
import Settings from './tabs/Settings';

// Shared utilities
import {
  API_BASE,
  fetchWithAuth,
  computeSubmissionStats,
} from './tabs/shared';

function EHC() {
  const toast = useToast();
  const { user, isAdmin } = useAuth();

  // Core state
  const [loading, setLoading] = useState(true);
  const [cycles, setCycles] = useState([]);
  const [activeCycle, setActiveCycle] = useState(null);
  const [view, setView] = useState('dashboard');

  // Data state (shared across tabs)
  const [dashboard, setDashboard] = useState(null);
  const [points, setPoints] = useState([]);
  const [records, setRecords] = useState([]);
  const [submissions, setSubmissions] = useState([]);

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCycleYear, setNewCycleYear] = useState(new Date().getFullYear());
  const [creatingCycle, setCreatingCycle] = useState(false);
  const [formLinkModalSubmission, setFormLinkModalSubmission] = useState(null);
  const [responseTrackerLink, setResponseTrackerLink] = useState(null);

  // Load cycles on mount
  useEffect(() => {
    loadCycles();
  }, []);

  // Load data when view or cycle changes
  useEffect(() => {
    if (!activeCycle) return;

    if (view === 'dashboard') {
      loadDashboard(activeCycle.id);
      loadSubmissions(activeCycle.id);
    } else if (view === 'points') {
      loadPoints(activeCycle.id);
      loadRecords();
    } else if (view === 'records') {
      loadRecords();
      loadSubmissions(activeCycle.id);
    }
  }, [activeCycle, view]);

  // === Data Loading Functions ===

  async function loadCycles() {
    try {
      setLoading(true);
      const data = await fetchWithAuth(`${API_BASE}/cycles`);
      setCycles(data.data || []);

      const active = data.data?.find(c => c.status === 'preparing' || c.status === 'in_progress') || data.data?.[0];
      setActiveCycle(active || null);
    } catch (error) {
      toast.error('Failed to load audit cycles');
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
      toast.error('Failed to load dashboard');
      console.error(error);
    }
  }

  async function loadPoints(cycleId) {
    try {
      const data = await fetchWithAuth(`${API_BASE}/cycles/${cycleId}/points`);
      setPoints(data.data || []);
    } catch (error) {
      toast.error('Failed to load audit points');
      console.error(error);
    }
  }

  async function loadRecords() {
    try {
      const data = await fetchWithAuth(`${API_BASE}/records`);
      const sorted = (data.data || []).sort((a, b) => {
        const numA = parseInt(a.record_number.replace(/\D/g, '')) || 0;
        const numB = parseInt(b.record_number.replace(/\D/g, '')) || 0;
        return numA - numB;
      });
      setRecords(sorted);
    } catch (error) {
      toast.error('Failed to load records');
      console.error(error);
    }
  }

  async function loadSubmissions(cycleId) {
    try {
      const data = await fetchWithAuth(`${API_BASE}/cycles/${cycleId}/submissions`);
      setSubmissions(data.data || []);
    } catch (error) {
      toast.error('Failed to load submissions');
      console.error(error);
    }
  }

  // === Cycle Management ===

  async function createCycle() {
    try {
      setCreatingCycle(true);
      await fetchWithAuth(`${API_BASE}/cycles`, {
        method: 'POST',
        body: JSON.stringify({ year: newCycleYear })
      });
      toast.success(`Audit cycle ${newCycleYear} created successfully!`);
      setShowCreateModal(false);
      loadCycles();
    } catch (error) {
      toast.error(error.message || 'Failed to create cycle');
    } finally {
      setCreatingCycle(false);
    }
  }

  async function updateAuditDate(dateString) {
    try {
      await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ target_date: dateString })
      });
      setActiveCycle(prev => ({ ...prev, target_date: dateString }));
      setCycles(prev => prev.map(c =>
        c.id === activeCycle.id ? { ...c, target_date: dateString } : c
      ));
      loadDashboard(activeCycle.id);
      toast.success('Audit date updated');
    } catch (error) {
      toast.error('Failed to update audit date');
    }
  }

  // === Audit Points Callbacks ===

  async function updatePointStatus(pointId, status) {
    try {
      await fetchWithAuth(`${API_BASE}/points/${pointId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status })
      });
      toast.success('Status updated');
      loadPoints(activeCycle.id);
      loadDashboard(activeCycle.id);
    } catch (error) {
      toast.error('Failed to update status');
    }
  }

  async function linkRecordToPoint(pointId, recordId) {
    try {
      await fetchWithAuth(`${API_BASE}/points/${pointId}/link-record`, {
        method: 'POST',
        body: JSON.stringify({ record_id: recordId })
      });
      toast.success('Record linked successfully');
      loadPoints(activeCycle.id);
      loadDashboard(activeCycle.id);
    } catch (error) {
      toast.error(error.message || 'Failed to link record');
    }
  }

  // === Helper Functions ===

  function getSubmissionStats() {
    return computeSubmissionStats(submissions);
  }

  function formatTargetDate() {
    if (!activeCycle?.target_date) return 'Set audit date';
    const date = new Date(activeCycle.target_date);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function getDaysUntilAudit() {
    if (!activeCycle?.target_date) return null;
    const target = new Date(activeCycle.target_date);
    const now = new Date();
    const days = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
    return days;
  }

  // === Render ===

  if (loading) {
    return (
      <div className="ehc-page">
        <Navigation />
        <div className="ehc-loading">
          <div className="loading-spinner"></div>
          <span>Loading EHC Module...</span>
        </div>
      </div>
    );
  }

  if (!activeCycle) {
    return (
      <div className="ehc-page">
        <Navigation />
        <div className="ehc-empty">
          <h2>No Audit Cycles</h2>
          <p>Create your first EHC audit cycle to get started.</p>
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            Create Audit Cycle
          </button>
        </div>

        {showCreateModal && (
          <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3>Create Audit Cycle</h3>
              <p>This will create a new EHC audit cycle and seed all 125 audit points.</p>
              <div className="modal-form">
                <label>
                  Year:
                  <input
                    type="number"
                    min="2024"
                    max="2030"
                    value={newCycleYear}
                    onChange={e => setNewCycleYear(parseInt(e.target.value))}
                  />
                </label>
                <div className="modal-actions">
                  <button className="btn-ghost" onClick={() => setShowCreateModal(false)}>Cancel</button>
                  <button className="btn-primary" onClick={createCycle} disabled={creatingCycle}>
                    {creatingCycle ? 'Creating...' : 'Create Cycle'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  const daysUntil = getDaysUntilAudit();
  const submissionStats = getSubmissionStats();

  return (
    <div className="ehc-page">
      <Navigation />

      {/* Header */}
      <div className="ehc-header">
        <div className="ehc-header-content">
          <div className="ehc-title-row">
            <h1>Environmental Health Compliance</h1>

            {/* Cycle selector */}
            <select
              className="cycle-select"
              value={activeCycle?.id || ''}
              onChange={e => {
                const cycle = cycles.find(c => c.id === parseInt(e.target.value));
                setActiveCycle(cycle);
              }}
            >
              {cycles.map(cycle => (
                <option key={cycle.id} value={cycle.id}>
                  EHC {cycle.year} — {cycle.status}
                </option>
              ))}
            </select>

            {/* Audit Date Picker */}
            <div className="audit-date-picker">
              <input
                type="date"
                value={activeCycle?.target_date?.split('T')[0] || ''}
                onChange={e => updateAuditDate(e.target.value)}
                className="audit-date-input"
              />
              <span className="audit-date-label">
                {formatTargetDate()}
                {daysUntil !== null && (
                  <span className={`days-countdown ${daysUntil <= 30 ? 'urgent' : ''}`}>
                    {daysUntil > 0 ? `${daysUntil} days` : daysUntil === 0 ? 'Today!' : `${Math.abs(daysUntil)} days ago`}
                  </span>
                )}
              </span>
            </div>
          </div>

          {/* 5-Tab Navigation */}
          <div className="ehc-tabs">
            <button
              className={`ehc-tab ${view === 'dashboard' ? 'active' : ''}`}
              onClick={() => setView('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`ehc-tab ${view === 'points' ? 'active' : ''}`}
              onClick={() => setView('points')}
            >
              Audit Points
            </button>
            <button
              className={`ehc-tab ${view === 'records' ? 'active' : ''}`}
              onClick={() => setView('records')}
            >
              Records
            </button>
            <button
              className={`ehc-tab ${view === 'forms' ? 'active' : ''}`}
              onClick={() => setView('forms')}
            >
              Forms
            </button>
            <button
              className={`ehc-tab ${view === 'settings' ? 'active' : ''}`}
              onClick={() => setView('settings')}
            >
              Settings
            </button>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="ehc-container">
        {view === 'dashboard' && (
          <Dashboard
            dashboard={dashboard}
            submissionStats={submissionStats}
          />
        )}

        {view === 'points' && (
          <AuditPoints
            points={points}
            setPoints={setPoints}
            records={records}
            activeCycle={activeCycle}
            onUpdatePointStatus={updatePointStatus}
            onLinkRecordToPoint={linkRecordToPoint}
            onRefreshDashboard={() => loadDashboard(activeCycle.id)}
            toast={toast}
          />
        )}

        {view === 'records' && (
          <Records
            records={records}
            submissions={submissions}
            setSubmissions={setSubmissions}
            activeCycle={activeCycle}
            onRefreshDashboard={() => loadDashboard(activeCycle.id)}
            onRefreshSubmissions={() => loadSubmissions(activeCycle.id)}
            onOpenFormLinkModal={setFormLinkModalSubmission}
            toast={toast}
          />
        )}

        {view === 'forms' && (
          <Forms activeCycle={activeCycle} />
        )}

        {view === 'settings' && (
          <Settings activeCycle={activeCycle} />
        )}
      </div>

      {/* Create Cycle Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Create Audit Cycle</h3>
            <p className="modal-description">
              This will create a new EHC audit cycle and seed all 125 audit points,
              6 sections, and 34 records from the master template.
            </p>
            <div className="modal-form">
              <label>
                Year:
                <input
                  type="number"
                  min="2024"
                  max="2030"
                  value={newCycleYear}
                  onChange={e => setNewCycleYear(parseInt(e.target.value))}
                />
              </label>
              <div className="modal-actions">
                <button className="btn-ghost" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button
                  className="btn-primary"
                  onClick={createCycle}
                  disabled={creatingCycle}
                >
                  {creatingCycle ? 'Creating...' : 'Create Cycle'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Form Link Modal */}
      <FormLinkModal
        isOpen={!!formLinkModalSubmission}
        onClose={() => setFormLinkModalSubmission(null)}
        submission={formLinkModalSubmission}
        onLinkCreated={data => {
          toast.showToast('Form link created', 'success');
        }}
        onViewResponses={link => {
          setResponseTrackerLink(link);
          setFormLinkModalSubmission(null);
        }}
      />

      {/* Response Tracker Modal */}
      <ResponseTrackerModal
        isOpen={!!responseTrackerLink}
        onClose={() => setResponseTrackerLink(null)}
        formLink={responseTrackerLink}
      />
    </div>
  );
}

export default EHC;
