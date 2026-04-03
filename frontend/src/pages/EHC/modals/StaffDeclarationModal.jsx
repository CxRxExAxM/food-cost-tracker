/**
 * Staff Declaration Form Creation Modal
 *
 * For Record 11 style forms:
 * - Pre-defined declaration content (23 food safety points)
 * - Staff scroll-to-sign and acknowledge
 * - Collect 50-100+ signatures
 */

import { useState, useEffect } from 'react';
import { API_BASE, fetchWithAuth } from '../tabs/shared';

export default function StaffDeclarationModal({
  isOpen,
  onClose,
  activeCycle,
  onFormCreated,
  toast
}) {
  const [title, setTitle] = useState('');
  const [expectedResponses, setExpectedResponses] = useState('95');
  const [creating, setCreating] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setTitle(`Food Safety Declaration - EHC ${activeCycle?.year || new Date().getFullYear()}`);
      setExpectedResponses('95');
    }
  }, [isOpen, activeCycle?.year]);

  async function handleCreate() {
    try {
      setCreating(true);

      const config = {
        document_ref: 'record_11',
        property_name: 'Fairmont Scottsdale Princess' // TODO: Get from org settings
      };

      // Record 11 is the staff declaration
      const payload = {
        form_type: 'staff_declaration',
        record_id: 11, // Record 11 ID - should lookup by record_number
        title: title || `Food Safety Declaration - EHC ${activeCycle.year}`,
        config,
        expected_responses: expectedResponses ? parseInt(expectedResponses) : null
      };

      // First, get the actual record ID for record_number = '11'
      const recordsData = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/records`);
      const record11 = recordsData.data.find(r => r.record_number === '11');

      if (!record11) {
        throw new Error('Record 11 not found');
      }

      payload.record_id = record11.id;

      const data = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/form-links`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      toast?.success?.('Staff Declaration form created');
      onFormCreated?.(data);
      onClose();
    } catch (error) {
      toast?.error?.(error.message || 'Failed to create form link');
    } finally {
      setCreating(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content form-create-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Staff Declaration Form</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <div className="form-type-info">
            <span className="form-type-icon">📋</span>
            <div>
              <strong>Record 11: Staff Food Safety Declaration</strong>
              <p>
                Staff will read the 23-point food safety declaration, scroll to the bottom,
                and sign to acknowledge. Perfect for annual food safety training acknowledgment.
              </p>
            </div>
          </div>

          <div className="form-field">
            <label>Form Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder={`Food Safety Declaration - EHC ${activeCycle?.year}`}
            />
          </div>

          <div className="form-field">
            <label>Expected Signatures</label>
            <input
              type="number"
              value={expectedResponses}
              onChange={e => setExpectedResponses(e.target.value)}
              placeholder="e.g., 95"
              min="1"
            />
            <span className="field-hint">
              How many staff need to sign? This helps track completion progress.
            </span>
          </div>

          <div className="modal-actions">
            <button className="btn-ghost" onClick={onClose}>Cancel</button>
            <button
              className="btn-primary"
              onClick={handleCreate}
              disabled={creating}
            >
              {creating ? 'Creating...' : 'Create Form Link'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
