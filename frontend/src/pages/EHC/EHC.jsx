import { useState, useEffect, useRef } from 'react';
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

// Location badge component
function LocationBadge({ type }) {
  const isOutlet = type === 'outlet_book';
  return (
    <span className={`location-badge ${isOutlet ? 'location-outlet' : 'location-office'}`}>
      {isOutlet ? 'Outlet Book' : 'Office Book'}
    </span>
  );
}

// Responsibility badge component
function ResponsibilityBadge({ code }) {
  const codeConfig = {
    MM: { label: 'MM', title: 'Mike / Audit Prep Manager' },
    CF: { label: 'CF', title: 'Chef (Executive Chef)' },
    CM: { label: 'CM', title: 'Commissary / Purchasing' },
    AM: { label: 'AM', title: 'Area Manager / Assistant Manager' },
    ENG: { label: 'ENG', title: 'Engineering' },
    FF: { label: 'FF', title: 'Facilities' },
    EHC: { label: 'EHC', title: 'External EHC Auditor' },
  };

  const config = codeConfig[code] || { label: code, title: code };

  return (
    <span className="responsibility-badge" title={config.title}>
      {config.label}
    </span>
  );
}

// Compute submission display status based on due dates
// Period ends → Due on 1st of next month → Past Due 2 weeks later
function getSubmissionDisplayStatus(submission) {
  // If already approved, that's the status
  if (submission.status === 'approved') {
    return { status: 'approved', label: 'Approved', class: 'badge-green' };
  }

  // Parse period to determine due date
  const periodLabel = submission.period_label || '';
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Try to parse "Month Year" format (e.g., "January 2026")
  const monthMatch = periodLabel.match(/^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$/i);

  if (monthMatch) {
    const monthNames = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
    const monthIndex = monthNames.indexOf(monthMatch[1].toLowerCase());
    const year = parseInt(monthMatch[2]);

    // Due date: 1st of next month
    const dueDate = new Date(year, monthIndex + 1, 1);
    // Past due: 2 weeks after due date
    const pastDueDate = new Date(dueDate);
    pastDueDate.setDate(pastDueDate.getDate() + 14);

    if (today >= pastDueDate) {
      return { status: 'past_due', label: 'Past Due', class: 'badge-red' };
    } else if (today >= dueDate) {
      return { status: 'due', label: 'Due', class: 'badge-yellow' };
    } else {
      return { status: 'pending', label: 'Pending', class: 'badge-neutral' };
    }
  }

  // Try to parse quarterly "Q1 2026" format
  const quarterMatch = periodLabel.match(/^Q([1-4])\s+(\d{4})$/i);
  if (quarterMatch) {
    const quarter = parseInt(quarterMatch[1]);
    const year = parseInt(quarterMatch[2]);
    // Q1 ends Mar 31, Q2 ends Jun 30, Q3 ends Sep 30, Q4 ends Dec 31
    const quarterEndMonth = quarter * 3; // 3, 6, 9, 12
    const dueDate = new Date(year, quarterEndMonth, 1); // 1st of month after quarter
    const pastDueDate = new Date(dueDate);
    pastDueDate.setDate(pastDueDate.getDate() + 14);

    if (today >= pastDueDate) {
      return { status: 'past_due', label: 'Past Due', class: 'badge-red' };
    } else if (today >= dueDate) {
      return { status: 'due', label: 'Due', class: 'badge-yellow' };
    } else {
      return { status: 'pending', label: 'Pending', class: 'badge-neutral' };
    }
  }

  // Default: show actual status if can't parse
  const statusMap = {
    pending: { status: 'pending', label: 'Pending', class: 'badge-neutral' },
    in_progress: { status: 'in_progress', label: 'In Progress', class: 'badge-yellow' },
    submitted: { status: 'submitted', label: 'Submitted', class: 'badge-blue' },
    not_applicable: { status: 'not_applicable', label: 'N/A', class: 'badge-neutral' },
  };
  return statusMap[submission.status] || { status: submission.status, label: submission.status, class: 'badge-neutral' };
}

// Submission status badge with computed due date logic
function SubmissionStatusBadge({ submission }) {
  const displayStatus = getSubmissionDisplayStatus(submission);
  return (
    <span className={`status-badge ${displayStatus.class}`} title={`DB status: ${submission.status}`}>
      {displayStatus.label}
    </span>
  );
}

// Record type badge
function RecordTypeBadge({ type }) {
  const typeLabels = {
    daily: 'Daily',
    monthly: 'Monthly',
    bi_monthly: 'Bi-Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
    one_time: 'One-Time',
    audit_window: 'Audit Window',
    as_needed: 'As Needed',
  };

  return (
    <span className="record-type-badge">
      {typeLabels[type] || type}
    </span>
  );
}

// Main EHC Component
function EHC() {
  const toast = useToast();
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
  const [creatingCycle, setCreatingCycle] = useState(false);

  // Records view state
  const [records, setRecords] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [recordFilters, setRecordFilters] = useState({
    locationType: null,
    recordType: null,
  });
  const [expandedRecord, setExpandedRecord] = useState(null);
  const [expandedPeriods, setExpandedPeriods] = useState(new Set()); // track expanded periods within records
  const [selectedSubmissions, setSelectedSubmissions] = useState(new Set());
  const [uploadingSubmission, setUploadingSubmission] = useState(null);

  // Inline editing state
  const [editingRecord, setEditingRecord] = useState(null); // record id being edited
  const [editingSubmission, setEditingSubmission] = useState(null); // submission id being edited
  const [editValues, setEditValues] = useState({});

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

  // Load records and submissions when view switches to records
  useEffect(() => {
    if (activeCycle && view === 'records') {
      loadRecords();
      loadSubmissions(activeCycle.id);
    }
  }, [activeCycle, view, recordFilters]);

  async function loadCycles() {
    try {
      setLoading(true);
      const data = await fetchWithAuth(`${API_BASE}/cycles`);
      setCycles(data.data || []);

      // Set active cycle to the most recent preparing/in_progress cycle
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
      let url = `${API_BASE}/cycles/${cycleId}/points?`;
      if (filters.section) url += `section=${filters.section}&`;
      if (filters.ncLevel) url += `nc_level=${filters.ncLevel}&`;
      if (filters.status) url += `status=${filters.status}&`;

      const data = await fetchWithAuth(url);
      setPoints(data.data || []);
    } catch (error) {
      toast.error('Failed to load audit points');
      console.error(error);
    }
  }

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

  async function updateAuditDate(dateString) {
    try {
      await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ target_date: dateString })
      });
      // Update local state
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

  async function loadRecords() {
    try {
      let url = `${API_BASE}/records?`;
      if (recordFilters.locationType) url += `location_type=${recordFilters.locationType}&`;
      if (recordFilters.recordType) url += `record_type=${recordFilters.recordType}&`;

      const data = await fetchWithAuth(url);

      // Sort records numerically by record_number
      const sorted = (data.data || []).sort((a, b) => {
        // Extract numeric part for sorting (handles "1", "1a", "SCP 40", etc.)
        const parseNum = (str) => {
          const match = str.match(/(\d+)/);
          return match ? parseInt(match[1], 10) : 999;
        };
        const aNum = parseNum(a.record_number);
        const bNum = parseNum(b.record_number);
        if (aNum !== bNum) return aNum - bNum;
        // Secondary sort by full string for "1" vs "1a"
        return a.record_number.localeCompare(b.record_number);
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

  async function updateSubmission(submissionId, updates) {
    // Optimistic update - update UI immediately
    setSubmissions(prev => prev.map(sub =>
      sub.id === submissionId ? { ...sub, ...updates } : sub
    ));

    try {
      await fetchWithAuth(`${API_BASE}/submissions/${submissionId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates)
      });
      // Only reload dashboard occasionally for status changes (affects stats)
      if (updates.status) {
        loadDashboard(activeCycle.id);
      }
    } catch (error) {
      toast.error('Failed to update submission');
      // Revert on failure - reload from server
      loadSubmissions(activeCycle.id);
    }
  }

  async function uploadSubmissionFile(submissionId, file) {
    try {
      setUploadingSubmission(submissionId);
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/submissions/${submissionId}/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      toast.success('File uploaded successfully');
      loadSubmissions(activeCycle.id);
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploadingSubmission(null);
    }
  }

  async function bulkUpdateSubmissions(status) {
    if (selectedSubmissions.size === 0) {
      toast.error('No submissions selected');
      return;
    }

    try {
      const promises = Array.from(selectedSubmissions).map(id =>
        fetchWithAuth(`${API_BASE}/submissions/${id}`, {
          method: 'PATCH',
          body: JSON.stringify({ status })
        })
      );
      await Promise.all(promises);
      toast.success(`${selectedSubmissions.size} submissions updated`);
      setSelectedSubmissions(new Set());
      loadSubmissions(activeCycle.id);
      loadDashboard(activeCycle.id);
    } catch (error) {
      toast.error('Failed to update submissions');
    }
  }

  // Get submissions for a specific record
  function getRecordSubmissions(recordId) {
    return submissions.filter(s => s.record_id === recordId);
  }

  // Calculate submission stats for a record (using computed due date status)
  function getRecordStats(recordId) {
    const recordSubs = getRecordSubmissions(recordId);
    const total = recordSubs.length;

    let approved = 0, due = 0, pastDue = 0, pending = 0;

    recordSubs.forEach(sub => {
      const displayStatus = getSubmissionDisplayStatus(sub);
      switch (displayStatus.status) {
        case 'approved': approved++; break;
        case 'due': due++; break;
        case 'past_due': pastDue++; break;
        default: pending++; break;
      }
    });

    return { total, approved, due, pastDue, pending };
  }

  // Group submissions by period for hierarchical view
  function groupSubmissionsByPeriod(recordSubs) {
    const groups = {};
    recordSubs.forEach(sub => {
      const period = sub.period_label;
      if (!groups[period]) {
        groups[period] = {
          period_label: period,
          period_start: sub.period_start,
          submissions: [],
        };
      }
      groups[period].submissions.push(sub);
    });

    // Sort periods chronologically (by period_start if available, else by label)
    return Object.values(groups).sort((a, b) => {
      if (a.period_start && b.period_start) {
        return new Date(a.period_start) - new Date(b.period_start);
      }
      return a.period_label.localeCompare(b.period_label);
    });
  }

  // Get stats for a period group
  function getPeriodStats(periodGroup) {
    const subs = periodGroup.submissions;
    const total = subs.length;
    const approved = subs.filter(s => s.status === 'approved').length;
    const allApproved = total > 0 && approved === total;
    return { total, approved, allApproved };
  }

  // Toggle period expansion
  function togglePeriod(recordId, periodLabel) {
    const key = `${recordId}-${periodLabel}`;
    setExpandedPeriods(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  // Check if period is expanded
  function isPeriodExpanded(recordId, periodLabel) {
    return expandedPeriods.has(`${recordId}-${periodLabel}`);
  }

  // Approve all submissions in a period
  async function approvePeriod(periodGroup) {
    const pendingSubs = periodGroup.submissions.filter(s => s.status !== 'approved');
    if (pendingSubs.length === 0) {
      toast.info('All submissions already approved');
      return;
    }
    try {
      await Promise.all(pendingSubs.map(sub =>
        fetchWithAuth(`${API_BASE}/submissions/${sub.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ status: 'approved' })
        })
      ));
      toast.success(`${pendingSubs.length} submissions approved`);
      loadSubmissions(activeCycle.id);
      loadDashboard(activeCycle.id);
    } catch (error) {
      toast.error('Failed to approve submissions');
    }
  }

  // Start editing a record (opens modal with all fields)
  function startEditingRecord(record) {
    setEditingRecord(record.id);
    setEditValues({
      name: record.name,
      notes: record.notes || '',
      record_type: record.record_type,
      location_type: record.location_type,
      description: record.description || '',
    });
    // Load outlets for this record
    loadRecordOutlets(record.id);
  }

  // Load outlets for a record
  async function loadRecordOutlets(recordId) {
    try {
      const data = await fetchWithAuth(`${API_BASE}/records/${recordId}/outlets`);
      setEditValues(prev => ({ ...prev, outlets: data.data || [] }));
    } catch (error) {
      console.error('Failed to load outlets', error);
    }
  }

  // Save record edits
  async function saveRecordEdit(recordId) {
    try {
      const { outlets, ...recordData } = editValues;
      await fetchWithAuth(`${API_BASE}/records/${recordId}`, {
        method: 'PATCH',
        body: JSON.stringify(recordData)
      });
      toast.success('Record updated');
      setEditingRecord(null);
      setEditValues({});
      loadRecords();
    } catch (error) {
      toast.error('Failed to update record');
    }
  }

  // Add outlet to record
  async function addRecordOutlet(recordId, outletName) {
    try {
      await fetchWithAuth(`${API_BASE}/records/${recordId}/outlets`, {
        method: 'POST',
        body: JSON.stringify({ outlet_name: outletName })
      });
      toast.success('Outlet added');
      loadRecordOutlets(recordId);
      loadRecords();
    } catch (error) {
      toast.error(error.message || 'Failed to add outlet');
    }
  }

  // Remove outlet from record
  async function removeRecordOutlet(recordId, outletName) {
    try {
      await fetchWithAuth(`${API_BASE}/records/${recordId}/outlets/${encodeURIComponent(outletName)}`, {
        method: 'DELETE'
      });
      toast.success('Outlet removed');
      loadRecordOutlets(recordId);
      loadRecords();
    } catch (error) {
      toast.error('Failed to remove outlet');
    }
  }

  // Cancel editing
  function cancelEdit() {
    setEditingRecord(null);
    setEditingSubmission(null);
    setEditValues({});
  }

  // Create a new submission
  async function createSubmission(recordId, periodLabel, outletName = null) {
    try {
      await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/submissions`, {
        method: 'POST',
        body: JSON.stringify({
          record_id: recordId,
          period_label: periodLabel,
          outlet_name: outletName,
        })
      });
      toast.success('Submission created');
      loadSubmissions(activeCycle.id);
    } catch (error) {
      toast.error(error.message || 'Failed to create submission');
    }
  }

  // Delete a submission (for cleaning up duplicates)
  async function deleteSubmission(submissionId) {
    if (!confirm('Delete this submission? This cannot be undone.')) return;
    try {
      await fetchWithAuth(`${API_BASE}/submissions/${submissionId}`, {
        method: 'DELETE'
      });
      toast.success('Submission deleted');
      loadSubmissions(activeCycle.id);
    } catch (error) {
      toast.error('Failed to delete submission');
    }
  }

  // Debounce ref for text input saves
  const saveTimeoutRef = useRef({});

  // Update local state immediately (optimistic)
  function updateSubmissionLocal(submissionId, field, value) {
    setSubmissions(prev => prev.map(sub =>
      sub.id === submissionId ? { ...sub, [field]: value } : sub
    ));
  }

  // Save to server (called directly or debounced)
  async function saveSubmissionField(submissionId, field, value) {
    try {
      await fetchWithAuth(`${API_BASE}/submissions/${submissionId}`, {
        method: 'PATCH',
        body: JSON.stringify({ [field]: value })
      });
    } catch (error) {
      toast.error('Failed to save');
      loadSubmissions(activeCycle.id); // Revert on failure
    }
  }

  // Update submission field - immediate local update, debounced save for text
  function updateSubmissionField(submissionId, field, value, debounce = false) {
    // Optimistic update - instant UI response
    updateSubmissionLocal(submissionId, field, value);

    if (debounce) {
      // Debounce API call for text inputs
      const key = `${submissionId}-${field}`;
      if (saveTimeoutRef.current[key]) {
        clearTimeout(saveTimeoutRef.current[key]);
      }
      saveTimeoutRef.current[key] = setTimeout(() => {
        saveSubmissionField(submissionId, field, value);
        delete saveTimeoutRef.current[key];
      }, 500);
    } else {
      // Immediate save for checkboxes/selects
      saveSubmissionField(submissionId, field, value);
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
                <button className="btn-primary" onClick={createCycle} disabled={creatingCycle}>
                  {creatingCycle ? 'Creating... (this takes a moment)' : 'Create Cycle'}
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

            {/* Audit Date Picker */}
            <div className="audit-date-picker">
              <label>Audit Date:</label>
              <input
                type="date"
                value={activeCycle?.target_date || ''}
                onChange={e => updateAuditDate(e.target.value)}
                className="date-input"
              />
            </div>

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
              <button
                className={`view-tab ${view === 'records' ? 'active' : ''}`}
                onClick={() => setView('records')}
              >
                Records
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
                            <div className="records-progress">
                              <span className="record-count" title={point.linked_record_names}>
                                {point.approved_submissions}/{point.total_submissions}
                              </span>
                              {point.total_submissions > 0 && (
                                <div className="mini-progress-bar">
                                  <div
                                    className="mini-progress-fill"
                                    style={{ width: `${(point.approved_submissions / point.total_submissions) * 100}%` }}
                                  />
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="no-records" title="Observational - no linked records">Obs</span>
                          )}
                        </td>
                        <td className="point-actions" onClick={e => e.stopPropagation()}>
                          {/* Only show manual status for observational points (no linked records) */}
                          {point.linked_record_count === 0 ? (
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
                          ) : (
                            <span className="auto-status" title="Status computed from records">
                              Auto
                            </span>
                          )}
                        </td>
                      </tr>
                      {expandedPoint === point.id && (
                        <tr className="point-expanded-row">
                          <td colSpan="7">
                            <div className="point-details">
                              <div className="point-detail-grid">
                                <div className="point-detail-section">
                                  <strong>Section:</strong> {point.section_name}
                                </div>
                                <div className="point-detail-section">
                                  <strong>Subsection:</strong> {point.subsection_code} - {point.subsection_name}
                                </div>
                                <div className="point-detail-section">
                                  <strong>Max Score:</strong> {point.max_score} pts
                                </div>
                              </div>
                              {point.notes && (
                                <div className="point-detail-section">
                                  <strong>Notes:</strong> {point.notes}
                                </div>
                              )}
                              {/* Linked Records */}
                              {point.linked_record_count > 0 && (
                                <div className="point-linked-records">
                                  <strong>Required Records:</strong>
                                  <div className="linked-records-list">
                                    {point.linked_record_names?.split(', ').map((rec, idx) => (
                                      <span key={idx} className="linked-record-chip">
                                        {rec}
                                      </span>
                                    ))}
                                  </div>
                                  <div className="completion-summary">
                                    {point.approved_submissions === point.total_submissions ? (
                                      <span className="completion-complete">All {point.total_submissions} submissions approved</span>
                                    ) : (
                                      <span className="completion-pending">
                                        {point.approved_submissions} of {point.total_submissions} submissions approved
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                              {point.linked_record_count === 0 && (
                                <div className="point-observational">
                                  <strong>Observational Point:</strong> Verified during audit walk-through (no linked records)
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

        {/* Records View */}
        {view === 'records' && (
          <div className="records-view">
            {/* Filters */}
            <div className="filters-bar">
              <select
                value={recordFilters.locationType || ''}
                onChange={e => setRecordFilters({ ...recordFilters, locationType: e.target.value || null })}
              >
                <option value="">All Locations</option>
                <option value="outlet_book">Outlet Book</option>
                <option value="office_book">Office Book</option>
              </select>

              <select
                value={recordFilters.recordType || ''}
                onChange={e => setRecordFilters({ ...recordFilters, recordType: e.target.value || null })}
              >
                <option value="">All Frequencies</option>
                <option value="daily">Daily</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
                <option value="as_needed">As Needed</option>
              </select>

              {(recordFilters.locationType || recordFilters.recordType) && (
                <button
                  className="btn-ghost"
                  onClick={() => setRecordFilters({ locationType: null, recordType: null })}
                >
                  Clear Filters
                </button>
              )}

              <span className="filter-count">{records.length} records</span>

              {/* Bulk Actions */}
              {selectedSubmissions.size > 0 && (
                <div className="bulk-actions">
                  <span className="bulk-count">{selectedSubmissions.size} selected</span>
                  <button className="btn-secondary btn-sm" onClick={() => bulkUpdateSubmissions('submitted')}>
                    Mark Submitted
                  </button>
                  <button className="btn-primary btn-sm" onClick={() => bulkUpdateSubmissions('approved')}>
                    Approve All
                  </button>
                  <button className="btn-ghost btn-sm" onClick={() => setSelectedSubmissions(new Set())}>
                    Clear
                  </button>
                </div>
              )}
            </div>

            {/* Records List */}
            <div className="records-list">
              {records.map(record => {
                const stats = getRecordStats(record.id);
                const recordSubs = getRecordSubmissions(record.id);
                const isExpanded = expandedRecord === record.id;

                return (
                  <div key={record.id} className={`record-card ${isExpanded ? 'expanded' : ''}`}>
                    <div className="record-header">
                      <div
                        className="record-info"
                        onClick={() => setExpandedRecord(isExpanded ? null : record.id)}
                      >
                        <span className="record-number">{record.record_number}</span>
                        <div className="record-details">
                          {editingRecord === record.id ? (
                            <input
                              type="text"
                              className="inline-edit-input"
                              value={editValues.name || ''}
                              onChange={e => setEditValues({ ...editValues, name: e.target.value })}
                              onClick={e => e.stopPropagation()}
                              autoFocus
                            />
                          ) : (
                            <span className="record-name">{record.name}</span>
                          )}
                          <div className="record-meta">
                            <LocationBadge type={record.location_type} />
                            <RecordTypeBadge type={record.record_type} />
                            {record.outlet_count > 0 && (
                              <span className="outlet-count">{record.outlet_count} outlets</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="record-actions-group">
                        {editingRecord === record.id ? (
                          <div className="edit-actions" onClick={e => e.stopPropagation()}>
                            <button className="btn-primary btn-sm" onClick={() => saveRecordEdit(record.id)}>
                              Save
                            </button>
                            <button className="btn-ghost btn-sm" onClick={cancelEdit}>
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            className="btn-ghost btn-sm edit-btn"
                            onClick={e => { e.stopPropagation(); startEditingRecord(record); }}
                            title="Edit record"
                          >
                            ✎
                          </button>
                        )}

                        <div className="record-stats" onClick={() => setExpandedRecord(isExpanded ? null : record.id)}>
                          <div className="record-progress-ring">
                            <svg width="48" height="48" viewBox="0 0 48 48">
                              <circle
                                cx="24" cy="24" r="20"
                                fill="transparent"
                                stroke="var(--border-subtle)"
                                strokeWidth="4"
                              />
                              <circle
                                cx="24" cy="24" r="20"
                                fill="transparent"
                                stroke={stats.approved === stats.total && stats.total > 0 ? 'var(--color-green)' : 'var(--color-yellow)'}
                                strokeWidth="4"
                                strokeLinecap="round"
                                strokeDasharray={`${stats.total > 0 ? (stats.approved / stats.total) * 125.6 : 0} 125.6`}
                                transform="rotate(-90 24 24)"
                              />
                            </svg>
                            <span className="record-progress-text">
                              {stats.total > 0 ? Math.round((stats.approved / stats.total) * 100) : 0}%
                            </span>
                          </div>
                          <div className="record-stats-text">
                            {stats.approved > 0 && <span className="stat-approved">{stats.approved} approved</span>}
                            {stats.pastDue > 0 && <span className="stat-past-due">{stats.pastDue} past due</span>}
                            {stats.due > 0 && <span className="stat-due">{stats.due} due</span>}
                            {stats.pending > 0 && <span className="stat-pending">{stats.pending} pending</span>}
                          </div>
                          <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>▼</span>
                        </div>
                      </div>
                    </div>

                    {/* Expanded Submissions - Two-Level Accordion */}
                    {isExpanded && (
                      <div className="record-submissions">
                        {/* For outlet_book records: group by period */}
                        {record.location_type === 'outlet_book' ? (
                          <>
                            <div className="period-list">
                              {groupSubmissionsByPeriod(recordSubs).map(periodGroup => {
                                const periodStats = getPeriodStats(periodGroup);
                                const periodExpanded = isPeriodExpanded(record.id, periodGroup.period_label);

                                return (
                                  <div key={periodGroup.period_label} className="period-accordion">
                                    {/* Period Header Row */}
                                    <div
                                      className={`period-header ${periodStats.allApproved ? 'all-approved' : ''}`}
                                      onClick={() => togglePeriod(record.id, periodGroup.period_label)}
                                    >
                                      <span className={`period-expand-icon ${periodExpanded ? 'expanded' : ''}`}>
                                        ▶
                                      </span>
                                      <span className="period-label">{periodGroup.period_label}</span>
                                      <span className={`period-progress ${periodStats.allApproved ? 'complete' : ''}`}>
                                        {periodStats.approved}/{periodStats.total}
                                      </span>
                                      {!periodStats.allApproved && (
                                        <button
                                          className="btn-approve-period"
                                          onClick={e => { e.stopPropagation(); approvePeriod(periodGroup); }}
                                          title="Approve all outlets for this period"
                                        >
                                          Approve All
                                        </button>
                                      )}
                                      {periodStats.allApproved && (
                                        <span className="period-complete-badge">Complete</span>
                                      )}
                                    </div>

                                    {/* Expanded Outlet Table */}
                                    {periodExpanded && (
                                      <div className="period-outlets">
                                        <table className="outlets-table">
                                          <thead>
                                            <tr>
                                              <th>Outlet</th>
                                              <th>Notes</th>
                                              <th>Physical</th>
                                              <th>File</th>
                                              <th>Status</th>
                                              <th></th>
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {periodGroup.submissions.map(sub => (
                                              <tr key={sub.id} className={`outlet-row status-${sub.status}`}>
                                                <td className="outlet-name-cell">{sub.outlet_name || '—'}</td>
                                                <td>
                                                  <input
                                                    type="text"
                                                    className="inline-notes-input"
                                                    value={sub.notes || ''}
                                                    placeholder="—"
                                                    onChange={e => updateSubmissionField(sub.id, 'notes', e.target.value, true)}
                                                  />
                                                </td>
                                                <td>
                                                  <input
                                                    type="checkbox"
                                                    checked={sub.is_physical}
                                                    onChange={e => updateSubmission(sub.id, { is_physical: e.target.checked })}
                                                  />
                                                </td>
                                                <td className="file-cell">
                                                  {uploadingSubmission === sub.id ? (
                                                    <span className="file-uploading">Uploading...</span>
                                                  ) : sub.file_path ? (
                                                    <div className="file-attached-group">
                                                      <a
                                                        href={`${API_BASE}/submissions/${sub.id}/download`}
                                                        className="file-link"
                                                        title={sub.original_filename || 'Download file'}
                                                        onClick={e => {
                                                          e.preventDefault();
                                                          // Download with auth header
                                                          const token = localStorage.getItem('token');
                                                          fetch(`${API_BASE}/submissions/${sub.id}/download`, {
                                                            headers: { 'Authorization': `Bearer ${token}` }
                                                          })
                                                          .then(res => res.blob())
                                                          .then(blob => {
                                                            const url = window.URL.createObjectURL(blob);
                                                            const a = document.createElement('a');
                                                            a.href = url;
                                                            a.download = sub.original_filename || 'file';
                                                            a.click();
                                                            window.URL.revokeObjectURL(url);
                                                          });
                                                        }}
                                                      >
                                                        {sub.original_filename
                                                          ? (sub.original_filename.length > 15
                                                            ? sub.original_filename.substring(0, 12) + '...'
                                                            : sub.original_filename)
                                                          : '📎'}
                                                      </a>
                                                      <label className="file-replace-btn" title="Replace file">
                                                        <input
                                                          type="file"
                                                          accept=".pdf,.jpg,.jpeg,.png,.docx,.xlsx"
                                                          onChange={e => {
                                                            if (e.target.files[0]) uploadSubmissionFile(sub.id, e.target.files[0]);
                                                          }}
                                                        />
                                                        ↻
                                                      </label>
                                                    </div>
                                                  ) : (
                                                    <label className="file-upload-label-sm">
                                                      <input
                                                        type="file"
                                                        accept=".pdf,.jpg,.jpeg,.png,.docx,.xlsx"
                                                        onChange={e => {
                                                          if (e.target.files[0]) uploadSubmissionFile(sub.id, e.target.files[0]);
                                                        }}
                                                      />
                                                      +
                                                    </label>
                                                  )}
                                                </td>
                                                <td className="status-cell">
                                                  <SubmissionStatusBadge submission={sub} />
                                                </td>
                                                <td className="actions-cell">
                                                  {sub.status !== 'approved' ? (
                                                    <button
                                                      className="btn-approve-sm"
                                                      onClick={() => updateSubmission(sub.id, { status: 'approved' })}
                                                      title="Approve"
                                                    >✓</button>
                                                  ) : (
                                                    <button
                                                      className="btn-unapprove-sm"
                                                      onClick={() => updateSubmission(sub.id, { status: 'pending' })}
                                                      title="Unapprove"
                                                    >↩</button>
                                                  )}
                                                  <button
                                                    className="btn-delete-sm"
                                                    onClick={() => deleteSubmission(sub.id)}
                                                    title="Delete"
                                                  >×</button>
                                                </td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>

                            {/* Add Submission Button */}
                            <div className="add-submission-row">
                              <button
                                className="btn-secondary btn-sm"
                                onClick={() => {
                                  const period = prompt('Enter period (e.g., "January 2026"):');
                                  if (period) {
                                    const outlet = prompt('Enter outlet name:');
                                    if (outlet) createSubmission(record.id, period, outlet);
                                  }
                                }}
                              >
                                + Add Submission
                              </button>
                            </div>
                          </>
                        ) : (
                          /* Office book records: flat list (no outlets) */
                          <>
                            <table className="submissions-table-flat">
                              <thead>
                                <tr>
                                  <th>Period</th>
                                  <th>Notes</th>
                                  <th>Physical</th>
                                  <th>File</th>
                                  <th>Status</th>
                                  <th></th>
                                </tr>
                              </thead>
                              <tbody>
                                {recordSubs.map(sub => (
                                  <tr key={sub.id} className={`submission-row status-${sub.status}`}>
                                    <td className="period-cell">{sub.period_label}</td>
                                    <td>
                                      <input
                                        type="text"
                                        className="inline-notes-input"
                                        value={sub.notes || ''}
                                        placeholder="—"
                                        onChange={e => updateSubmissionField(sub.id, 'notes', e.target.value, true)}
                                      />
                                    </td>
                                    <td>
                                      <input
                                        type="checkbox"
                                        checked={sub.is_physical}
                                        onChange={e => updateSubmission(sub.id, { is_physical: e.target.checked })}
                                      />
                                    </td>
                                    <td className="file-cell">
                                      {uploadingSubmission === sub.id ? (
                                        <span className="file-uploading">Uploading...</span>
                                      ) : sub.file_path ? (
                                        <div className="file-attached-group">
                                          <a
                                            href={`${API_BASE}/submissions/${sub.id}/download`}
                                            className="file-link"
                                            title={sub.original_filename || 'Download file'}
                                            onClick={e => {
                                              e.preventDefault();
                                              const token = localStorage.getItem('token');
                                              fetch(`${API_BASE}/submissions/${sub.id}/download`, {
                                                headers: { 'Authorization': `Bearer ${token}` }
                                              })
                                              .then(res => res.blob())
                                              .then(blob => {
                                                const url = window.URL.createObjectURL(blob);
                                                const a = document.createElement('a');
                                                a.href = url;
                                                a.download = sub.original_filename || 'file';
                                                a.click();
                                                window.URL.revokeObjectURL(url);
                                              });
                                            }}
                                          >
                                            {sub.original_filename
                                              ? (sub.original_filename.length > 15
                                                ? sub.original_filename.substring(0, 12) + '...'
                                                : sub.original_filename)
                                              : '📎'}
                                          </a>
                                          <label className="file-replace-btn" title="Replace file">
                                            <input
                                              type="file"
                                              accept=".pdf,.jpg,.jpeg,.png,.docx,.xlsx"
                                              onChange={e => {
                                                if (e.target.files[0]) uploadSubmissionFile(sub.id, e.target.files[0]);
                                              }}
                                            />
                                            ↻
                                          </label>
                                        </div>
                                      ) : (
                                        <label className="file-upload-label-sm">
                                          <input
                                            type="file"
                                            accept=".pdf,.jpg,.jpeg,.png,.docx,.xlsx"
                                            onChange={e => {
                                              if (e.target.files[0]) uploadSubmissionFile(sub.id, e.target.files[0]);
                                            }}
                                          />
                                          +
                                        </label>
                                      )}
                                    </td>
                                    <td className="status-cell">
                                      <SubmissionStatusBadge submission={sub} />
                                    </td>
                                    <td className="actions-cell">
                                      {sub.status !== 'approved' ? (
                                        <button
                                          className="btn-approve-sm"
                                          onClick={() => updateSubmission(sub.id, { status: 'approved' })}
                                          title="Approve"
                                        >✓</button>
                                      ) : (
                                        <button
                                          className="btn-unapprove-sm"
                                          onClick={() => updateSubmission(sub.id, { status: 'pending' })}
                                          title="Unapprove"
                                        >↩</button>
                                      )}
                                      <button
                                        className="btn-delete-sm"
                                        onClick={() => deleteSubmission(sub.id)}
                                        title="Delete"
                                      >×</button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>

                            <div className="add-submission-row">
                              <button
                                className="btn-secondary btn-sm"
                                onClick={() => {
                                  const period = prompt('Enter period (e.g., "Annual 2026", "Q1 2026"):');
                                  if (period) createSubmission(record.id, period, null);
                                }}
                              >
                                + Add Submission
                              </button>
                            </div>
                          </>
                        )}

                        {recordSubs.length === 0 && (
                          <div className="no-submissions">
                            No submissions for this record. Click "Add Submission" to create one.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {records.length === 0 && (
                <div className="no-results">
                  No records match your filters.
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

      {/* Edit Record Modal */}
      {editingRecord && (
        <div className="modal-overlay" onClick={cancelEdit}>
          <div className="modal-content modal-wide" onClick={e => e.stopPropagation()}>
            <h3>Edit Record</h3>

            <div className="form-row">
              <div className="form-group flex-2">
                <label>Record Name</label>
                <input
                  type="text"
                  value={editValues.name || ''}
                  onChange={e => setEditValues({ ...editValues, name: e.target.value })}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Location</label>
                <select
                  value={editValues.location_type || ''}
                  onChange={e => setEditValues({ ...editValues, location_type: e.target.value })}
                >
                  <option value="outlet_book">Outlet Book</option>
                  <option value="office_book">Office Book</option>
                </select>
              </div>

              <div className="form-group">
                <label>Frequency</label>
                <select
                  value={editValues.record_type || ''}
                  onChange={e => setEditValues({ ...editValues, record_type: e.target.value })}
                >
                  <option value="daily">Daily</option>
                  <option value="monthly">Monthly</option>
                  <option value="bi_monthly">Bi-Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="annual">Annual</option>
                  <option value="one_time">One-Time</option>
                  <option value="as_needed">As Needed</option>
                </select>
              </div>

            </div>

            <div className="form-group">
              <label>Description / Notes</label>
              <textarea
                value={editValues.notes || ''}
                onChange={e => setEditValues({ ...editValues, notes: e.target.value })}
                rows={3}
                placeholder="Add any notes about this record..."
              />
            </div>

            {/* Outlet Assignments (for outlet_book records) */}
            {editValues.location_type === 'outlet_book' && (
              <div className="form-group">
                <label>Assigned Outlets</label>
                <div className="outlet-chips">
                  {(editValues.outlets || []).map(outlet => (
                    <span key={outlet.outlet_name} className="outlet-chip">
                      {outlet.outlet_name}
                      <button
                        className="chip-remove"
                        onClick={() => removeRecordOutlet(editingRecord, outlet.outlet_name)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <button
                    className="btn-add-outlet"
                    onClick={() => {
                      const name = prompt('Enter outlet name:');
                      if (name) addRecordOutlet(editingRecord, name);
                    }}
                  >
                    + Add Outlet
                  </button>
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn-secondary" onClick={cancelEdit}>
                Cancel
              </button>
              <button className="btn-primary" onClick={() => saveRecordEdit(editingRecord)}>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EHC;
