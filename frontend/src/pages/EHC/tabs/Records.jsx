/**
 * Records Tab Component
 *
 * Manages EHC record submissions with two-level accordion (outlet book vs office book),
 * file uploads, inline editing, and bulk actions.
 */

import { useState, useRef } from 'react';
import { Link } from 'lucide-react';
import {
  LocationBadge,
  RecordTypeBadge,
  SubmissionStatusBadge,
  getSubmissionDisplayStatus,
  computeSubmissionStats,
  API_BASE,
  fetchWithAuth,
} from './shared';

export default function Records({
  records,
  submissions,
  setSubmissions,
  activeCycle,
  onRefreshDashboard,
  onRefreshSubmissions,
  onOpenFormLinkModal,
  toast,
}) {
  // Local UI state
  const [recordFilters, setRecordFilters] = useState({
    locationType: null,
    recordType: null,
  });
  const [expandedRecord, setExpandedRecord] = useState(null);
  const [expandedPeriods, setExpandedPeriods] = useState(new Set());
  const [selectedSubmissions, setSelectedSubmissions] = useState(new Set());
  const [uploadingSubmission, setUploadingSubmission] = useState(null);

  // Inline editing state
  const [editingRecord, setEditingRecord] = useState(null);
  const [editValues, setEditValues] = useState({});

  // Debounce ref for notes
  const debounceRef = useRef({});

  // Filter records
  const filteredRecords = records.filter(r => {
    if (recordFilters.locationType && r.location_type !== recordFilters.locationType) return false;
    if (recordFilters.recordType && r.record_type !== recordFilters.recordType) return false;
    return true;
  });

  // Get submissions for a specific record
  function getRecordSubmissions(recordId) {
    return submissions.filter(s => s.record_id === recordId);
  }

  // Calculate submission stats for a record
  function getRecordStats(recordId) {
    const recordSubs = getRecordSubmissions(recordId);
    return computeSubmissionStats(recordSubs);
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
      onRefreshSubmissions();
      onRefreshDashboard();
    } catch (error) {
      toast.error('Failed to approve submissions');
    }
  }

  // Update submission with optimistic UI
  async function updateSubmission(submissionId, updates) {
    setSubmissions(prev => prev.map(sub =>
      sub.id === submissionId ? { ...sub, ...updates } : sub
    ));

    try {
      await fetchWithAuth(`${API_BASE}/submissions/${submissionId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates)
      });
      if (updates.status) {
        onRefreshDashboard();
      }
    } catch (error) {
      toast.error('Failed to update submission');
      onRefreshSubmissions();
    }
  }

  // Update submission field with optional debounce
  function updateSubmissionField(submissionId, field, value, debounce = false) {
    // Update local state immediately
    setSubmissions(prev => prev.map(sub =>
      sub.id === submissionId ? { ...sub, [field]: value } : sub
    ));

    if (debounce) {
      // Clear existing timeout
      if (debounceRef.current[submissionId]) {
        clearTimeout(debounceRef.current[submissionId]);
      }
      // Set new timeout
      debounceRef.current[submissionId] = setTimeout(() => {
        fetchWithAuth(`${API_BASE}/submissions/${submissionId}`, {
          method: 'PATCH',
          body: JSON.stringify({ [field]: value })
        }).catch(() => {
          toast.error('Failed to save');
        });
      }, 500);
    } else {
      updateSubmission(submissionId, { [field]: value });
    }
  }

  // Upload file to submission
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
      onRefreshSubmissions();
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploadingSubmission(null);
    }
  }

  // Bulk update selected submissions
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
      onRefreshSubmissions();
      onRefreshDashboard();
    } catch (error) {
      toast.error('Failed to update submissions');
    }
  }

  // Create new submission
  async function createSubmission(recordId, periodLabel, outletName = null) {
    try {
      await fetchWithAuth(`${API_BASE}/submissions`, {
        method: 'POST',
        body: JSON.stringify({
          audit_cycle_id: activeCycle.id,
          record_id: recordId,
          period_label: periodLabel,
          outlet_name: outletName
        })
      });
      toast.success('Submission created');
      onRefreshSubmissions();
    } catch (error) {
      toast.error(error.message || 'Failed to create submission');
    }
  }

  // Delete submission
  async function deleteSubmission(submissionId) {
    if (!confirm('Delete this submission? This cannot be undone.')) return;

    try {
      await fetchWithAuth(`${API_BASE}/submissions/${submissionId}`, {
        method: 'DELETE'
      });
      toast.success('Submission deleted');
      onRefreshSubmissions();
      onRefreshDashboard();
    } catch (error) {
      toast.error('Failed to delete submission');
    }
  }

  // Record editing functions
  function startEditingRecord(record) {
    setEditingRecord(record.id);
    setEditValues({
      name: record.name,
      notes: record.notes || ''
    });
  }

  async function saveRecordEdit(recordId) {
    try {
      await fetchWithAuth(`${API_BASE}/records/${recordId}`, {
        method: 'PATCH',
        body: JSON.stringify(editValues)
      });
      toast.success('Record updated');
      setEditingRecord(null);
      // Note: Would need onRefreshRecords callback to refresh records list
    } catch (error) {
      toast.error('Failed to update record');
    }
  }

  function cancelEdit() {
    setEditingRecord(null);
    setEditValues({});
  }

  // Download file with auth
  function downloadFile(submissionId, filename) {
    const token = localStorage.getItem('token');
    fetch(`${API_BASE}/submissions/${submissionId}/download`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'file';
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  return (
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

        <span className="filter-count">{filteredRecords.length} records</span>

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
        {filteredRecords.map(record => {
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

              {/* Expanded Submissions */}
              {isExpanded && (
                <div className="record-submissions">
                  {record.location_type === 'outlet_book' ? (
                    // Outlet book: grouped by period
                    <>
                      <div className="period-list">
                        {groupSubmissionsByPeriod(recordSubs).map(periodGroup => {
                          const periodStats = getPeriodStats(periodGroup);
                          const periodExpanded = isPeriodExpanded(record.id, periodGroup.period_label);

                          return (
                            <div key={periodGroup.period_label} className="period-accordion">
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
                                                  href="#"
                                                  className="file-link"
                                                  title={sub.original_filename || 'Download file'}
                                                  onClick={e => {
                                                    e.preventDefault();
                                                    downloadFile(sub.id, sub.original_filename);
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
                                            <button
                                              className="btn-link-sm"
                                              onClick={() => onOpenFormLinkModal({
                                                id: sub.id,
                                                record_name: record.name,
                                                period_label: sub.period_label,
                                                outlet_name: sub.outlet_name
                                              })}
                                              title="Form Link"
                                            >
                                              <Link size={12} />
                                            </button>
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
                    // Office book: flat list
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
                                      href="#"
                                      className="file-link"
                                      title={sub.original_filename || 'Download file'}
                                      onClick={e => {
                                        e.preventDefault();
                                        downloadFile(sub.id, sub.original_filename);
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
                                <button
                                  className="btn-link-sm"
                                  onClick={() => onOpenFormLinkModal({
                                    id: sub.id,
                                    record_name: record.name,
                                    period_label: sub.period_label,
                                    outlet_name: null
                                  })}
                                  title="Form Link"
                                >
                                  <Link size={12} />
                                </button>
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

        {filteredRecords.length === 0 && (
          <div className="no-results">
            No records match your filters.
          </div>
        )}
      </div>
    </div>
  );
}
