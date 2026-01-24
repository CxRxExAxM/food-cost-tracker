import { useState, useEffect } from 'react';
import axios from '../../../lib/axios';
import UnitSelect from '../../../components/UnitSelect';
import VesselSelect from '../../../components/VesselSelect';

const AMOUNT_MODES = [
  { value: 'per_person', label: 'Per Person', description: 'Scales with guest count' },
  { value: 'at_minimum', label: 'At Minimum', description: 'Fixed amount based on min guests' },
  { value: 'fixed', label: 'Fixed', description: 'Same amount regardless of guests' },
  { value: 'vessel', label: 'By Vessel', description: 'Based on vessel capacity' }
];

function EditPrepItemModal({ prepItem, onClose, onPrepItemUpdated }) {
  // Determine initial mode based on existing data
  const getInitialMode = () => {
    if (prepItem.vessel_id && prepItem.vessel_count) {
      return 'vessel';
    }
    return prepItem.amount_mode || 'per_person';
  };

  const [formData, setFormData] = useState({
    name: prepItem.name || '',
    amount_mode: getInitialMode(),
    amount_per_guest: prepItem.amount_per_guest || '',
    base_amount: prepItem.base_amount || '',
    unit_id: prepItem.unit_id || null,
    amount_unit: prepItem.amount_unit || '', // Legacy fallback
    vessel_id: prepItem.vessel_id || null,
    vessel_count: prepItem.vessel_count || '',
    vessel: prepItem.vessel || '', // Legacy text field
    responsibility: prepItem.responsibility || ''
  });

  const [selectedVessel, setSelectedVessel] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Load vessel details if prepItem has vessel_id
  useEffect(() => {
    if (prepItem.vessel_id) {
      const loadVessel = async () => {
        try {
          const response = await axios.get(`/vessels/${prepItem.vessel_id}`);
          setSelectedVessel(response.data);
        } catch (err) {
          console.error('Error loading vessel:', err);
        }
      };
      loadVessel();
    }
  }, [prepItem.vessel_id]);

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

  const handleModeChange = (mode) => {
    setFormData(prev => ({
      ...prev,
      amount_mode: mode,
      // Clear fields when switching modes
      ...(mode === 'vessel' ? { amount_per_guest: '', base_amount: '' } : {}),
      ...(mode !== 'vessel' ? { vessel_id: null, vessel_count: '' } : {})
    }));
    if (mode !== 'vessel') {
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

      // Set amount mode (use 'per_person' for vessel mode since vessel_id handles it)
      if (formData.amount_mode === 'vessel') {
        payload.amount_mode = 'per_person'; // Default mode when using vessel
        payload.vessel_id = formData.vessel_id;
        payload.vessel_count = formData.vessel_count ? parseFloat(formData.vessel_count) : null;
        // Clear standard amount fields
        payload.amount_per_guest = null;
        payload.base_amount = null;
      } else {
        payload.amount_mode = formData.amount_mode;
        // Clear vessel fields
        payload.vessel_id = null;
        payload.vessel_count = null;

        if (formData.amount_mode === 'per_person') {
          payload.amount_per_guest = formData.amount_per_guest ? parseFloat(formData.amount_per_guest) : null;
          payload.base_amount = null;
        } else {
          // at_minimum or fixed
          payload.base_amount = formData.base_amount ? parseFloat(formData.base_amount) : null;
          payload.amount_per_guest = null;
        }
      }

      // Unit (prefer unit_id, fallback to legacy amount_unit)
      if (formData.unit_id) {
        payload.unit_id = formData.unit_id;
        payload.amount_unit = null; // Clear legacy field
      } else if (formData.amount_unit) {
        payload.amount_unit = formData.amount_unit;
        payload.unit_id = null;
      } else {
        payload.unit_id = null;
        payload.amount_unit = null;
      }

      // Legacy vessel text (if not using vessel_id)
      if (!formData.vessel_id && formData.vessel) {
        payload.vessel = formData.vessel;
      } else {
        payload.vessel = null;
      }

      await axios.put(`/banquet-menus/prep/${prepItem.id}`, payload);

      onPrepItemUpdated();
    } catch (err) {
      console.error('Error updating prep item:', err);
      setError(err.response?.data?.detail || 'Failed to update prep item');
    } finally {
      setSaving(false);
    }
  };

  const isVesselMode = formData.amount_mode === 'vessel';

  // Calculate preview for vessel mode
  const vesselPreview = () => {
    if (!isVesselMode || !selectedVessel || !formData.vessel_count) return null;
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
          <h2>Edit Prep Item</h2>
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

            {/* Amount Mode Selector */}
            <div className="form-group">
              <label>Amount Type</label>
              <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                {AMOUNT_MODES.map(mode => (
                  <button
                    key={mode.value}
                    type="button"
                    onClick={() => handleModeChange(mode.value)}
                    style={{
                      padding: 'var(--space-2) var(--space-3)',
                      borderRadius: 'var(--radius-md)',
                      border: formData.amount_mode === mode.value
                        ? '2px solid var(--primary)'
                        : '1px solid var(--border-color)',
                      backgroundColor: formData.amount_mode === mode.value
                        ? 'var(--primary-light)'
                        : 'var(--surface-color)',
                      cursor: 'pointer',
                      fontSize: 'var(--text-sm)'
                    }}
                    title={mode.description}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                {AMOUNT_MODES.find(m => m.value === formData.amount_mode)?.description}
              </p>
            </div>

            {/* Standard Amount Fields (non-vessel modes) */}
            {!isVesselMode && (
              <div className="form-row">
                <div className="form-group">
                  <label>
                    {formData.amount_mode === 'per_person' ? 'Amount Per Guest' : 'Amount'}
                  </label>
                  <input
                    type="number"
                    name={formData.amount_mode === 'per_person' ? 'amount_per_guest' : 'base_amount'}
                    className="form-input"
                    value={formData.amount_mode === 'per_person' ? formData.amount_per_guest : formData.base_amount}
                    onChange={handleChange}
                    placeholder="0.5"
                    step="0.0001"
                    min="0"
                  />
                </div>

                <div className="form-group">
                  <label>Unit</label>
                  <UnitSelect
                    value={formData.unit_id}
                    onChange={handleChange}
                    name="unit_id"
                  />
                </div>
              </div>
            )}

            {/* Vessel-based Amount Fields */}
            {isVesselMode && (
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
            {!isVesselMode && (
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

            {isVesselMode && (
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
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EditPrepItemModal;
