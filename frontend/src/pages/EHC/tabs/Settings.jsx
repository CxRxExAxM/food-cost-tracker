/**
 * Settings Tab Component
 *
 * Module configuration:
 * - Audit cycle management (status, dates)
 * - Section overview and progress
 * - NC level reference
 * - Future: Outlets, contacts, responsibility codes
 */

import { useState } from 'react';
import {
  API_BASE,
  fetchWithAuth,
  NCBadge,
} from './shared';

export default function Settings({ activeCycle, onCycleUpdated, toast }) {
  const [updating, setUpdating] = useState(false);
  const [showStatusConfirm, setShowStatusConfirm] = useState(null);

  const cycleStatuses = [
    { value: 'preparing', label: 'Preparing', description: 'Setting up records and collecting evidence' },
    { value: 'in_progress', label: 'In Progress', description: 'Audit is underway' },
    { value: 'completed', label: 'Completed', description: 'Audit finished and reviewed' },
    { value: 'archived', label: 'Archived', description: 'Historical record' },
  ];

  async function updateCycleStatus(newStatus) {
    try {
      setUpdating(true);
      await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
      toast?.success?.(`Cycle status updated to ${newStatus.replace('_', ' ')}`);
      onCycleUpdated?.();
      setShowStatusConfirm(null);
    } catch (error) {
      toast?.error?.('Failed to update cycle status');
    } finally {
      setUpdating(false);
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Not set';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getDaysUntil = (dateStr) => {
    if (!dateStr) return null;
    const target = new Date(dateStr);
    const now = new Date();
    const days = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
    return days;
  };

  const daysUntil = getDaysUntil(activeCycle?.target_date);

  return (
    <div className="settings-view-content">
      {/* Cycle Overview */}
      <section className="settings-section">
        <h2>Audit Cycle Overview</h2>

        <div className="settings-card">
          <div className="cycle-info-grid">
            <div className="info-item">
              <span className="info-label">Cycle</span>
              <span className="info-value large">EHC {activeCycle?.year}</span>
            </div>

            <div className="info-item">
              <span className="info-label">Status</span>
              <span className={`status-badge ${activeCycle?.status}`}>
                {activeCycle?.status?.replace('_', ' ')}
              </span>
            </div>

            <div className="info-item">
              <span className="info-label">Audit Date</span>
              <span className="info-value">
                {formatDate(activeCycle?.target_date)}
                {daysUntil !== null && (
                  <span className={`days-badge ${daysUntil <= 30 ? 'urgent' : ''}`}>
                    {daysUntil > 0
                      ? `${daysUntil} days away`
                      : daysUntil === 0
                        ? 'Today!'
                        : `${Math.abs(daysUntil)} days ago`}
                  </span>
                )}
              </span>
            </div>

            <div className="info-item">
              <span className="info-label">Created</span>
              <span className="info-value">{formatDate(activeCycle?.created_at)}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Status Management */}
      <section className="settings-section">
        <h2>Cycle Status</h2>
        <p className="section-description">
          Update the cycle status to reflect the current phase of the audit.
        </p>

        <div className="status-options">
          {cycleStatuses.map(status => (
            <div
              key={status.value}
              className={`status-option ${activeCycle?.status === status.value ? 'current' : ''}`}
            >
              <div className="status-option-header">
                <span className={`status-indicator ${status.value}`}></span>
                <strong>{status.label}</strong>
                {activeCycle?.status === status.value && (
                  <span className="current-label">Current</span>
                )}
              </div>
              <p className="status-description">{status.description}</p>
              {activeCycle?.status !== status.value && (
                <button
                  className="btn-sm"
                  onClick={() => setShowStatusConfirm(status.value)}
                  disabled={updating}
                >
                  Set as {status.label}
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Status change confirmation */}
        {showStatusConfirm && (
          <div className="confirm-dialog">
            <p>
              Change cycle status to <strong>{showStatusConfirm.replace('_', ' ')}</strong>?
            </p>
            <div className="confirm-actions">
              <button
                className="btn-ghost"
                onClick={() => setShowStatusConfirm(null)}
                disabled={updating}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={() => updateCycleStatus(showStatusConfirm)}
                disabled={updating}
              >
                {updating ? 'Updating...' : 'Confirm'}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* NC Level Reference */}
      <section className="settings-section">
        <h2>NC Level Reference</h2>
        <p className="section-description">
          Non-conformance levels and their scoring impact.
        </p>

        <div className="nc-reference-grid">
          <div className="nc-reference-item">
            <NCBadge level={1} />
            <div className="nc-details">
              <strong>Critical</strong>
              <p>Immediate food safety risk. Requires immediate correction.</p>
              <span className="nc-impact">High impact on audit score</span>
            </div>
          </div>

          <div className="nc-reference-item">
            <NCBadge level={2} />
            <div className="nc-details">
              <strong>Operational</strong>
              <p>Operational food safety issue. Correction within 24–48 hours.</p>
              <span className="nc-impact">Moderate impact on audit score</span>
            </div>
          </div>

          <div className="nc-reference-item">
            <NCBadge level={3} />
            <div className="nc-details">
              <strong>Structural</strong>
              <p>Infrastructure or equipment issue. Plan for correction.</p>
              <span className="nc-impact">Lower impact on audit score</span>
            </div>
          </div>

          <div className="nc-reference-item">
            <NCBadge level={4} />
            <div className="nc-details">
              <strong>Administrative</strong>
              <p>Documentation or record-keeping issue. Low risk.</p>
              <span className="nc-impact">Minimal impact on audit score</span>
            </div>
          </div>
        </div>
      </section>

      {/* Future Features */}
      <section className="settings-section future">
        <h2>Coming Soon</h2>
        <div className="future-features">
          <div className="future-feature">
            <span className="feature-icon">🏪</span>
            <div>
              <strong>EHC Outlets</strong>
              <p>Manage kitchen areas and restaurants for signature collection</p>
            </div>
          </div>

          <div className="future-feature">
            <span className="feature-icon">👥</span>
            <div>
              <strong>Leader Contacts</strong>
              <p>Configure email distribution for reports and notifications</p>
            </div>
          </div>

          <div className="future-feature">
            <span className="feature-icon">📋</span>
            <div>
              <strong>Responsibility Codes</strong>
              <p>Define area ownership and escalation paths</p>
            </div>
          </div>

          <div className="future-feature">
            <span className="feature-icon">📊</span>
            <div>
              <strong>Scoring Configuration</strong>
              <p>Customize NC level weights and thresholds</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
