/**
 * Audit Points Tab Component
 *
 * Displays all 125+ audit points with filtering, inline editing,
 * internal verification checkboxes, and record linking.
 */

import { useState, Fragment } from 'react';
import {
  NCBadge,
  StatusBadge,
  API_BASE,
  fetchWithAuth,
} from './shared';

export default function AuditPoints({
  points,
  setPoints,
  records,
  activeCycle,
  onUpdatePointStatus,
  onLinkRecordToPoint,
  onRefreshDashboard,
  toast,
}) {
  // Local state for this tab
  const [filters, setFilters] = useState({
    section: null,
    ncLevel: null,
    status: null,
  });
  const [expandedPoint, setExpandedPoint] = useState(null);
  const [linkRecordPointId, setLinkRecordPointId] = useState(null);
  const [linkRecordSearch, setLinkRecordSearch] = useState('');

  // Filter points based on local filters
  const filteredPoints = points.filter(point => {
    if (filters.section && point.section_ref !== parseInt(filters.section)) return false;
    if (filters.ncLevel && point.nc_level !== parseInt(filters.ncLevel)) return false;
    if (filters.status && point.status !== filters.status) return false;
    return true;
  });

  // Handle internal verification checkbox
  async function handleInternalVerified(point, newValue) {
    // Optimistic update
    setPoints(prev => prev.map(p =>
      p.id === point.id ? { ...p, internal_verified: newValue } : p
    ));

    try {
      await fetchWithAuth(`${API_BASE}/points/${point.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ internal_verified: newValue })
      });
      onRefreshDashboard();
    } catch (error) {
      // Revert on error
      setPoints(prev => prev.map(p =>
        p.id === point.id ? { ...p, internal_verified: !newValue } : p
      ));
      toast.error('Failed to update');
    }
  }

  // Handle record linking
  function handleLinkRecord(pointId, recordId) {
    onLinkRecordToPoint(pointId, recordId);
    setLinkRecordPointId(null);
    setLinkRecordSearch('');
  }

  return (
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

        <span className="filter-count">{filteredPoints.length} points</span>
      </div>

      {/* Points Table */}
      <div className="points-table-container">
        <table className="points-table">
          <thead>
            <tr>
              <th>Ref</th>
              <th>Question</th>
              <th>NC</th>
              <th>Internal ✓</th>
              <th>Status</th>
              <th>Area</th>
              <th>Records</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredPoints.map(point => (
              <Fragment key={point.id}>
                <tr
                  className={`point-row ${expandedPoint === point.id ? 'expanded' : ''}`}
                  onClick={() => setExpandedPoint(expandedPoint === point.id ? null : point.id)}
                >
                  <td className="point-ref">{point.ref_code}</td>
                  <td className="point-question">{point.question_text}</td>
                  <td><NCBadge level={point.nc_level} /></td>
                  <td className="point-internal" onClick={e => e.stopPropagation()}>
                    {/* Internal verification checkbox - only for observational points */}
                    {point.linked_record_count === 0 ? (
                      <input
                        type="checkbox"
                        checked={point.internal_verified || false}
                        onChange={e => handleInternalVerified(point, e.target.checked)}
                        title="Internal walk verification"
                      />
                    ) : (
                      <span className="internal-na" title="Record-based point">—</span>
                    )}
                  </td>
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
                        onChange={e => onUpdatePointStatus(point.id, e.target.value)}
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

                {/* Expanded Row */}
                {expandedPoint === point.id && (
                  <tr className="point-expanded-row">
                    <td colSpan="8">
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
                                <span className="completion-complete">
                                  All {point.total_submissions} submissions approved
                                </span>
                              ) : (
                                <span className="completion-pending">
                                  {point.approved_submissions} of {point.total_submissions} submissions approved
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Observational Point - Link Record UI */}
                        {point.linked_record_count === 0 && (
                          <div className="point-observational">
                            <div className="obs-header">
                              <strong>Observational Point</strong>
                              <button
                                className="btn-link"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setLinkRecordPointId(linkRecordPointId === point.id ? null : point.id);
                                  setLinkRecordSearch('');
                                }}
                              >
                                {linkRecordPointId === point.id ? 'Cancel' : '+ Link Record'}
                              </button>
                            </div>
                            {linkRecordPointId !== point.id && (
                              <p className="obs-description">
                                Verified during audit walk-through. Click "Link Record" to associate a required record.
                              </p>
                            )}
                            {linkRecordPointId === point.id && (
                              <div className="link-record-search" onClick={e => e.stopPropagation()}>
                                <input
                                  type="text"
                                  placeholder="Search records by number or name..."
                                  value={linkRecordSearch}
                                  onChange={e => setLinkRecordSearch(e.target.value)}
                                  autoFocus
                                />
                                <div className="link-record-results">
                                  {records
                                    .filter(r =>
                                      linkRecordSearch &&
                                      (r.record_number.toLowerCase().includes(linkRecordSearch.toLowerCase()) ||
                                       r.name.toLowerCase().includes(linkRecordSearch.toLowerCase()))
                                    )
                                    .slice(0, 8)
                                    .map(r => (
                                      <div
                                        key={r.id}
                                        className="link-record-option"
                                        onClick={() => handleLinkRecord(point.id, r.id)}
                                      >
                                        <span className="record-number">{r.record_number}</span>
                                        <span className="record-name">{r.name}</span>
                                      </div>
                                    ))
                                  }
                                  {linkRecordSearch && records.filter(r =>
                                    r.record_number.toLowerCase().includes(linkRecordSearch.toLowerCase()) ||
                                    r.name.toLowerCase().includes(linkRecordSearch.toLowerCase())
                                  ).length === 0 && (
                                    <div className="link-record-empty">No matching records found</div>
                                  )}
                                  {!linkRecordSearch && (
                                    <div className="link-record-hint">Type to search records...</div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>

        {filteredPoints.length === 0 && (
          <div className="no-results">
            No audit points match your filters.
          </div>
        )}
      </div>
    </div>
  );
}
