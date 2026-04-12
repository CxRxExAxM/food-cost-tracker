/**
 * Contact Modal Component
 *
 * Create/edit EHC contacts with outlet assignments.
 * Each contact can be assigned to multiple outlets with primary flag.
 */

import { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';

export default function ContactModal({
  contact,
  outlets,
  onSave,
  onDelete,
  onClose
}) {
  // Initialize form data from contact prop
  const initialFormData = contact ? {
    id: contact.id,
    name: contact.name || '',
    email: contact.email || '',
    title: contact.title || '',
    is_active: contact.is_active ?? true,
  } : {
    name: '',
    email: '',
    title: '',
    is_active: true,
  };

  const initialOutlets = contact?.outlets
    ? contact.outlets.map(o => ({
        outlet_id: o.outlet_id,
        is_primary: o.is_primary || false
      }))
    : [];

  const [formData, setFormData] = useState(initialFormData);
  const [outletAssignments, setOutletAssignments] = useState(initialOutlets);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function toggleOutlet(outletId) {
    setOutletAssignments(prev => {
      const exists = prev.find(a => a.outlet_id === outletId);
      if (exists) {
        // Remove
        return prev.filter(a => a.outlet_id !== outletId);
      } else {
        // Add
        return [...prev, { outlet_id: outletId, is_primary: false }];
      }
    });
  }

  function togglePrimary(outletId) {
    setOutletAssignments(prev =>
      prev.map(a =>
        a.outlet_id === outletId
          ? { ...a, is_primary: !a.is_primary }
          : a
      )
    );
  }

  function isOutletAssigned(outletId) {
    return outletAssignments.some(a => a.outlet_id === outletId);
  }

  function isOutletPrimary(outletId) {
    return outletAssignments.find(a => a.outlet_id === outletId)?.is_primary || false;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.name.trim()) {
      setError('Name is required');
      return;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return;
    }
    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Please enter a valid email address');
      return;
    }

    try {
      setSaving(true);
      await onSave(formData, outletAssignments);
    } catch (err) {
      setError(err.message || 'Failed to save contact');
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (contact?.id) {
      setSaving(true);
      await onDelete(contact.id);
      setSaving(false);
    }
  }

  // Group outlets by type for display
  const outletsByType = outlets.reduce((acc, outlet) => {
    const type = outlet.outlet_type || 'Other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(outlet);
    return acc;
  }, {});

  const typeOrder = ['Production Kitchen', 'Restaurant', 'Bar', 'Lounge', 'Support', 'Franchise', 'Other'];
  const sortedTypes = typeOrder.filter(type => outletsByType[type]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container modal-lg" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{contact ? 'Edit Contact' : 'Add Contact'}</h2>
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

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="contact-name">
                Name <span className="required">*</span>
              </label>
              <input
                id="contact-name"
                type="text"
                className="input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Juan Garcia"
                maxLength={255}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="contact-email">
                Email <span className="required">*</span>
              </label>
              <input
                id="contact-email"
                type="email"
                className="input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="jgarcia@fairmont.com"
                maxLength={255}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="contact-title">Title / Role</label>
            <input
              id="contact-title"
              type="text"
              className="input"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Executive Sous Chef"
              maxLength={255}
            />
          </div>

          {/* Outlet Assignments */}
          <div className="form-group">
            <label>Outlet Assignments</label>
            <p className="form-help">
              Select outlets this contact is responsible for. Mark one as "Primary" for automatic email distribution.
            </p>

            <div className="outlet-assignment-grid">
              {sortedTypes.map(type => (
                <div key={type} className="outlet-type-section">
                  <span className="outlet-type-label">{type}</span>
                  <div className="outlet-checkboxes">
                    {outletsByType[type].map(outlet => (
                      <div key={outlet.id} className="outlet-assignment-row">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={isOutletAssigned(outlet.id)}
                            onChange={() => toggleOutlet(outlet.id)}
                          />
                          <span className="outlet-name">{outlet.name}</span>
                          {outlet.full_name && outlet.full_name !== outlet.name && (
                            <span className="outlet-full-name">({outlet.full_name})</span>
                          )}
                        </label>
                        {isOutletAssigned(outlet.id) && (
                          <button
                            type="button"
                            className={`primary-toggle ${isOutletPrimary(outlet.id) ? 'is-primary' : ''}`}
                            onClick={() => togglePrimary(outlet.id)}
                            title={isOutletPrimary(outlet.id) ? 'Primary contact' : 'Set as primary'}
                          >
                            {isOutletPrimary(outlet.id) ? (
                              <>
                                <Check size={12} />
                                Primary
                              </>
                            ) : (
                              'Set Primary'
                            )}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {contact && (
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
          )}
        </form>

        <div className="modal-footer">
          <div className="modal-footer-left">
            {contact && (
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
              {saving ? 'Saving...' : contact ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
