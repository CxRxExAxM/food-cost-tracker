import { useState } from 'react';
import axios from '../../../lib/axios';

function EditItemModal({ item, onClose, onItemUpdated }) {
  const [formData, setFormData] = useState({
    name: item.name || '',
    is_enhancement: item.is_enhancement === 1,
    additional_price: item.additional_price || '',
    price: item.price || ''
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
        additional_price: formData.additional_price ? parseFloat(formData.additional_price) : null,
        price: formData.price ? parseFloat(formData.price) : null
      };

      await axios.put(`/banquet-menus/items/${item.id}`, payload);

      onItemUpdated();
    } catch (err) {
      console.error('Error updating menu item:', err);
      setError(err.response?.data?.detail || 'Failed to update menu item');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Menu Item</h2>
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
              <label>Item Price (for cost % calculation)</label>
              <input
                type="number"
                name="price"
                className="form-input"
                value={formData.price}
                onChange={handleChange}
                placeholder="52.00"
                step="0.01"
                min="0"
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
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EditItemModal;
