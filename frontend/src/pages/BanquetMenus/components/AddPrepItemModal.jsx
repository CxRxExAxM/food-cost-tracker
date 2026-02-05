import { useState } from 'react';
import axios from '../../../lib/axios';
import UnitSelect from '../../../components/UnitSelect';
import VesselSelect from '../../../components/VesselSelect';

function AddPrepItemModal({ menuItemId, onClose, onPrepItemAdded, menuType = 'banquet' }) {
  const isRestaurant = menuType === 'restaurant';
  const [formData, setFormData] = useState({
    name: '',
    useVessel: false,
    amount_per_guest: '',
    guests_per_amount: '1',  // Default: per 1 guest (per person)
    unit_id: null,
    amount_unit: '', // Legacy fallback
    vessel_id: null,
    vessel_count: '',
    vessel: '', // Legacy text field
    responsibility: ''
  });
  const [selectedVessel, setSelectedVessel] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Track selected vessel for capacity display
    if (name === 'vessel_id' && e.target.vessel) {
      setSelectedVessel(e.target.vessel);
    } else if (name === 'vessel_id' && !value) {
      setSelectedVessel(null);
    }
  };

  const toggleVesselMode = (useVessel) => {
    setFormData(prev => ({
      ...prev,
      useVessel,
      // Clear fields when switching modes
      ...(useVessel ? { amount_per_guest: '', guests_per_amount: '1' } : {}),
      ...(!useVessel ? { vessel_id: null, vessel_count: '' } : {})
    }));
    if (!useVessel) {
      setSelectedVessel(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.name) {
      setError('Please enter a prep item name');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formData.name,
        responsibility: formData.responsibility || null
      };

      if (formData.useVessel) {
        // Vessel mode
        payload.vessel_id = formData.vessel_id;
        payload.vessel_count = formData.vessel_count ? parseFloat(formData.vessel_count) : null;
      } else {
        // Standard "per X guests" mode
        payload.amount_per_guest = formData.amount_per_guest ? parseFloat(formData.amount_per_guest) : null;
        payload.guests_per_amount = formData.guests_per_amount ? parseInt(formData.guests_per_amount) : 1;
      }

      // Unit (prefer unit_id, fallback to legacy amount_unit)
      if (formData.unit_id) {
        payload.unit_id = formData.unit_id;
      } else if (formData.amount_unit) {
        payload.amount_unit = formData.amount_unit;
      }

      // Legacy vessel text (if not using vessel_id)
      if (!formData.vessel_id && formData.vessel) {
        payload.vessel = formData.vessel;
      }

      await axios.post(`/banquet-menus/items/${menuItemId}/prep`, payload);

      onPrepItemAdded();
    } catch (err) {
      console.error('Error adding prep item:', err);
      setError(err.response?.data?.detail || 'Failed to add prep item');
    } finally {
      setSaving(false);
    }
  };

  // Calculate preview for vessel mode
  const vesselPreview = () => {
    if (!formData.useVessel || !selectedVessel || !formData.vessel_count) return null;
    const count = parseFloat(formData.vessel_count) || 0;
    const capacity = parseFloat(selectedVessel.default_capacity) || 0;
    const total = count * capacity;
    const unit = selectedVessel.default_unit_abbr || '';
    return `= ${total} ${unit}`;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Prep Item</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label>Prep Item Name *</label>
              <input
                type="text"
                name="name"
                className="form-input"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Dried Fruit, Brown Sugar"
                required
                autoFocus
              />
            </div>

            {/* Amount Type Toggle */}
            <div className="form-group">
              <label>Amount Type</label>
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <button
                  type="button"
                  onClick={() => toggleVesselMode(false)}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    border: !formData.useVessel
                      ? '2px solid var(--primary)'
                      : '1px solid var(--border-color)',
                    backgroundColor: !formData.useVessel
                      ? 'var(--primary-light)'
                      : 'var(--surface-color)',
                    cursor: 'pointer',
                    fontSize: 'var(--text-sm)'
                  }}
                >
                  {isRestaurant ? 'Fixed Amount' : 'Per Guests'}
                </button>
                <button
                  type="button"
                  onClick={() => toggleVesselMode(true)}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    border: formData.useVessel
                      ? '2px solid var(--primary)'
                      : '1px solid var(--border-color)',
                    backgroundColor: formData.useVessel
                      ? 'var(--primary-light)'
                      : 'var(--surface-color)',
                    cursor: 'pointer',
                    fontSize: 'var(--text-sm)'
                  }}
                >
                  By Vessel
                </button>
              </div>
            </div>

            {/* Standard Amount Fields (per X guests for banquet, fixed for restaurant) */}
            {!formData.useVessel && (
              <div className="form-group">
                <label>Amount{isRestaurant ? ' (per portion)' : ''}</label>
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="number"
                    name="amount_per_guest"
                    className="form-input"
                    style={{ width: '80px' }}
                    value={formData.amount_per_guest}
                    onChange={handleChange}
                    placeholder="2"
                    step="0.0001"
                    min="0"
                  />
                  <div style={{ width: '100px' }}>
                    <UnitSelect
                      value={formData.unit_id}
                      onChange={handleChange}
                      name="unit_id"
                    />
                  </div>
                  {!isRestaurant && (
                    <>
                      <span style={{ color: 'var(--text-secondary)' }}>per</span>
                      <input
                        type="number"
                        name="guests_per_amount"
                        className="form-input"
                        style={{ width: '60px' }}
                        value={formData.guests_per_amount}
                        onChange={handleChange}
                        placeholder="1"
                        min="1"
                      />
                      <span style={{ color: 'var(--text-secondary)' }}>guest(s)</span>
                    </>
                  )}
                </div>
                {!isRestaurant && (
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                    e.g., "2 OZ per 1 guest" or "1 bottle per 10 guests"
                  </p>
                )}
              </div>
            )}

            {/* Vessel-based Amount Fields */}
            {formData.useVessel && (
              <>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Vessel</label>
                    <VesselSelect
                      value={formData.vessel_id}
                      onChange={handleChange}
                      name="vessel_id"
                    />
                  </div>

                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Count</label>
                    <input
                      type="number"
                      name="vessel_count"
                      className="form-input"
                      value={formData.vessel_count}
                      onChange={handleChange}
                      placeholder="2"
                      step="0.5"
                      min="0"
                    />
                  </div>
                </div>

                {vesselPreview() && (
                  <div style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--surface-secondary)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--text-sm)',
                    color: 'var(--text-secondary)',
                    marginBottom: 'var(--space-3)'
                  }}>
                    Calculated: {vesselPreview()}
                  </div>
                )}
              </>
            )}

            {/* Legacy vessel text field (only show if not using vessel mode) */}
            {!formData.useVessel && (
              <div className="form-row">
                <div className="form-group">
                  <label>Vessel (optional text)</label>
                  <input
                    type="text"
                    name="vessel"
                    className="form-input"
                    value={formData.vessel}
                    onChange={handleChange}
                    placeholder="e.g., Chafing Dish, Pitcher"
                  />
                </div>

                <div className="form-group">
                  <label>Responsibility (optional)</label>
                  <input
                    type="text"
                    name="responsibility"
                    className="form-input"
                    value={formData.responsibility}
                    onChange={handleChange}
                    placeholder="e.g., Hot Line, Pantry"
                  />
                </div>
              </div>
            )}

            {formData.useVessel && (
              <div className="form-group">
                <label>Responsibility (optional)</label>
                <input
                  type="text"
                  name="responsibility"
                  className="form-input"
                  value={formData.responsibility}
                  onChange={handleChange}
                  placeholder="e.g., Hot Line, Pantry"
                />
              </div>
            )}

            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-4)' }}>
              You can link this prep item to a product or recipe after creating it.
            </p>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Adding...' : 'Add Prep Item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPrepItemModal;
