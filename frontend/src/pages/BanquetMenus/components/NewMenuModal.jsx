import { useState } from 'react';
import axios from '../../../lib/axios';

function NewMenuModal({ outletId, onClose, onMenuCreated }) {
  const [formData, setFormData] = useState({
    meal_period: '',
    service_type: '',
    name: '',
    price_per_person: '',
    min_guest_count: '',
    under_min_surcharge: '',
    target_food_cost_pct: ''
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

    if (!formData.meal_period || !formData.service_type || !formData.name) {
      setError('Please fill in all required fields');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        outlet_id: outletId,
        meal_period: formData.meal_period,
        service_type: formData.service_type,
        name: formData.name,
        price_per_person: formData.price_per_person ? parseFloat(formData.price_per_person) : null,
        min_guest_count: formData.min_guest_count ? parseInt(formData.min_guest_count, 10) : null,
        under_min_surcharge: formData.under_min_surcharge ? parseFloat(formData.under_min_surcharge) : null,
        target_food_cost_pct: formData.target_food_cost_pct ? parseFloat(formData.target_food_cost_pct) : null
      };

      const response = await axios.post('/banquet-menus', payload);

      onMenuCreated({
        id: response.data.menu_id,
        meal_period: formData.meal_period,
        service_type: formData.service_type,
        name: formData.name
      });
    } catch (err) {
      console.error('Error creating menu:', err);
      setError(err.response?.data?.detail || 'Failed to create menu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>New Banquet Menu</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label>Meal Period *</label>
              <input
                type="text"
                name="meal_period"
                className="form-input"
                value={formData.meal_period}
                onChange={handleChange}
                placeholder="e.g., Breakfast, Lunch, Dinner"
                required
              />
            </div>

            <div className="form-group">
              <label>Service Type *</label>
              <input
                type="text"
                name="service_type"
                className="form-input"
                value={formData.service_type}
                onChange={handleChange}
                placeholder="e.g., Buffet, Plated, Passed"
                required
              />
            </div>

            <div className="form-group">
              <label>Menu Name *</label>
              <input
                type="text"
                name="name"
                className="form-input"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Good Morning Starter"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Price Per Person</label>
                <input
                  type="number"
                  name="price_per_person"
                  className="form-input"
                  value={formData.price_per_person}
                  onChange={handleChange}
                  placeholder="80.00"
                  step="0.01"
                  min="0"
                />
              </div>

              <div className="form-group">
                <label>Target Food Cost %</label>
                <input
                  type="number"
                  name="target_food_cost_pct"
                  className="form-input"
                  value={formData.target_food_cost_pct}
                  onChange={handleChange}
                  placeholder="28"
                  step="0.1"
                  min="0"
                  max="100"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Minimum Guests</label>
                <input
                  type="number"
                  name="min_guest_count"
                  className="form-input"
                  value={formData.min_guest_count}
                  onChange={handleChange}
                  placeholder="50"
                  min="1"
                />
              </div>

              <div className="form-group">
                <label>Surcharge (per person)</label>
                <input
                  type="number"
                  name="under_min_surcharge"
                  className="form-input"
                  value={formData.under_min_surcharge}
                  onChange={handleChange}
                  placeholder="10.00"
                  step="0.01"
                  min="0"
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Creating...' : 'Create Menu'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default NewMenuModal;
