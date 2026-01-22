import { useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function AddItemModal({ menuId, onClose, onItemAdded }) {
  const [formData, setFormData] = useState({
    name: '',
    is_enhancement: false,
    additional_price: ''
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.name) {
      setError('Please enter an item name');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formData.name,
        is_enhancement: formData.is_enhancement,
        additional_price: formData.additional_price ? parseFloat(formData.additional_price) : null
      };

      await axios.post(`${API_URL}/api/banquet-menus/${menuId}/items`, payload, {
        withCredentials: true
      });

      onItemAdded();
    } catch (err) {
      console.error('Error adding menu item:', err);
      setError(err.response?.data?.detail || 'Failed to add menu item');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Menu Item</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label>Item Name *</label>
              <input
                type="text"
                name="name"
                className="form-input"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Oatmeal, Farm Fresh Scrambled Eggs"
                required
                autoFocus
              />
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="is_enhancement"
                  checked={formData.is_enhancement}
                  onChange={handleChange}
                  style={{ width: '18px', height: '18px' }}
                />
                This is an enhancement/add-on
              </label>
            </div>

            {formData.is_enhancement && (
              <div className="form-group">
                <label>Additional Price (per person)</label>
                <input
                  type="number"
                  name="additional_price"
                  className="form-input"
                  value={formData.additional_price}
                  onChange={handleChange}
                  placeholder="15.00"
                  step="0.01"
                  min="0"
                />
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Adding...' : 'Add Item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddItemModal;
