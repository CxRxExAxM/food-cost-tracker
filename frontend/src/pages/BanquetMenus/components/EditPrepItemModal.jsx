import { useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function EditPrepItemModal({ prepItem, onClose, onPrepItemUpdated }) {
  const [formData, setFormData] = useState({
    name: prepItem.name || '',
    amount_per_guest: prepItem.amount_per_guest || '',
    amount_unit: prepItem.amount_unit || '',
    vessel: prepItem.vessel || '',
    responsibility: prepItem.responsibility || ''
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
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
        amount_per_guest: formData.amount_per_guest ? parseFloat(formData.amount_per_guest) : null,
        amount_unit: formData.amount_unit || null,
        vessel: formData.vessel || null,
        responsibility: formData.responsibility || null
      };

      await axios.put(`${API_URL}/api/banquet-menus/prep/${prepItem.id}`, payload, {
        withCredentials: true
      });

      onPrepItemUpdated();
    } catch (err) {
      console.error('Error updating prep item:', err);
      setError(err.response?.data?.detail || 'Failed to update prep item');
    } finally {
      setSaving(false);
    }
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

            <div className="form-row">
              <div className="form-group">
                <label>Amount Per Guest</label>
                <input
                  type="number"
                  name="amount_per_guest"
                  className="form-input"
                  value={formData.amount_per_guest}
                  onChange={handleChange}
                  placeholder="0.5"
                  step="0.0001"
                  min="0"
                />
              </div>

              <div className="form-group">
                <label>Unit</label>
                <input
                  type="text"
                  name="amount_unit"
                  className="form-input"
                  value={formData.amount_unit}
                  onChange={handleChange}
                  placeholder="e.g., oz, each, cups"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Vessel (optional)</label>
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
