/**
 * Outlet Modal Component
 *
 * Create/edit EHC outlets (kitchens, restaurants, bars, etc.)
 * Leader assignment is handled via Contacts (not on this form).
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

export default function OutletModal({ outlet, outletTypes, onSave, onDelete, onClose }) {
  const [formData, setFormData] = useState({
    name: '',
    full_name: '',
    outlet_type: 'Production Kitchen',
    is_active: true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (outlet) {
      setFormData({
        id: outlet.id,
        name: outlet.name || '',
        full_name: outlet.full_name || '',
        outlet_type: outlet.outlet_type || 'Production Kitchen',
        is_active: outlet.is_active ?? true,
      });
    }
  }, [outlet]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.name.trim()) {
      setError('Name is required');
      return;
    }

    if (formData.name.length > 50) {
      setError('Name must be 50 characters or less');
      return;
    }

    try {
      setSaving(true);
      await onSave(formData);
    } catch (err) {
      setError(err.message || 'Failed to save outlet');
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (outlet?.id) {
      setSaving(true);
      await onDelete(outlet.id);
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{outlet ? 'Edit Outlet' : 'Add Outlet'}</h2>
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
            <label htmlFor="outlet-name">
              Name (tag) <span className="required">*</span>
            </label>
            <input
              id="outlet-name"
              type="text"
              className="input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="MK, Toro, LaHa"
              maxLength={50}
              required
            />
            <span className="form-help">Short name used as tag/pill (e.g., MK, Toro)</span>
          </div>

          <div className="form-group">
            <label htmlFor="outlet-full-name">Full Name</label>
            <input
              id="outlet-full-name"
              type="text"
              className="input"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              placeholder="Main Kitchen"
              maxLength={255}
            />
            <span className="form-help">Display name (e.g., Main Kitchen, Toro Latin Restaurant & Rum Bar)</span>
          </div>

          <div className="form-group">
            <label htmlFor="outlet-type">Type</label>
            <select
              id="outlet-type"
              className="input"
              value={formData.outlet_type}
              onChange={(e) => setFormData({ ...formData, outlet_type: e.target.value })}
            >
              {outletTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              />
              <span>Active</span>
            </label>
          </div>
        </form>

        <div className="modal-footer">
          <div className="modal-footer-left">
            {outlet && (
              <button
                type="button"
                className="btn-danger-ghost"
                onClick={handleDelete}
                disabled={saving}
              >
                Deactivate
              </button>
            )}
          </div>
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
              {saving ? 'Saving...' : outlet ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
