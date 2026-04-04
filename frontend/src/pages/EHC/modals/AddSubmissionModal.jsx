/**
 * Add Submission Modal Component
 *
 * Modal for creating new record submissions with:
 * - Period label input (e.g., "January 2026", "Q1 2026", "Annual 2026")
 * - Optional outlet selection (for outlet book records)
 * - Uses OutletPillSelector for outlet selection
 */

import { useState } from 'react';
import { X } from 'lucide-react';
import OutletPillSelector from '../../../components/EHC/shared/OutletPillSelector';

export default function AddSubmissionModal({
  record,
  locationType, // 'outlet_book' or 'office_book'
  onSave,
  onClose
}) {
  const [formData, setFormData] = useState({
    period_label: '',
    outlet: null
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const isOutletBook = locationType === 'outlet_book';

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.period_label.trim()) {
      setError('Period label is required');
      return;
    }

    if (isOutletBook && !formData.outlet) {
      setError('Please select an outlet');
      return;
    }

    try {
      setSaving(true);
      const outletName = isOutletBook ? (formData.outlet.name || formData.outlet) : null;
      await onSave(record.id, formData.period_label, outletName);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create submission');
      setSaving(false);
    }
  }

  // Common period suggestions
  const currentYear = new Date().getFullYear();
  const periodSuggestions = [
    `Annual ${currentYear}`,
    `Q1 ${currentYear}`,
    `Q2 ${currentYear}`,
    `Q3 ${currentYear}`,
    `Q4 ${currentYear}`,
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Submission</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-group">
            <label>Record</label>
            <div className="record-display">
              <span className="record-number">#{record.number}</span>
              <span className="record-name">{record.name}</span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="period-label">
              Period Label <span className="required">*</span>
            </label>
            <input
              id="period-label"
              type="text"
              className="input"
              value={formData.period_label}
              onChange={(e) => setFormData({ ...formData, period_label: e.target.value })}
              placeholder="e.g., January 2026, Q1 2026, Annual 2026"
              required
              list="period-suggestions"
            />
            <datalist id="period-suggestions">
              {periodSuggestions.map(period => (
                <option key={period} value={period} />
              ))}
            </datalist>
            <span className="form-help">
              {isOutletBook
                ? 'Monthly periods (e.g., "January 2026") or other recurring labels'
                : 'Annual or quarterly periods (e.g., "Annual 2026", "Q1 2026")'
              }
            </span>
          </div>

          {isOutletBook && (
            <div className="form-group">
              <label>
                Outlet <span className="required">*</span>
              </label>
              <OutletPillSelector
                selected={formData.outlet}
                onChange={(outlet) => setFormData({ ...formData, outlet })}
                multiSelect={false}
              />
              <span className="form-help">
                Select which outlet this submission is for
              </span>
            </div>
          )}
        </form>

        <div className="modal-footer">
          <div className="modal-footer-left"></div>
          <div className="modal-footer-right">
            <button
              type="button"
              className="btn-ghost"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              onClick={handleSubmit}
              disabled={saving}
            >
              {saving ? 'Creating...' : 'Create Submission'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
