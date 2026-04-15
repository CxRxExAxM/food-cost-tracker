/**
 * Outlet Modal Component
 *
 * Create/edit EHC outlets (kitchens, restaurants, bars, etc.)
 * Includes daily monitoring configuration (Phase 1 of Daily Monitoring Module).
 */

import { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronUp, Thermometer } from 'lucide-react';

export default function OutletModal({ outlet, outletTypes, onSave, onDelete, onClose }) {
  const [formData, setFormData] = useState({
    name: '',
    full_name: '',
    outlet_type: 'Production Kitchen',
    is_active: true,
    // Daily monitoring configuration
    daily_monitoring_enabled: false,
    cooler_count: 0,
    freezer_count: 0,
    has_cooking: false,
    has_cooling: false,
    has_thawing: false,
    has_hot_buffet: false,
    has_cold_buffet: false,
    serves_breakfast: false,
    serves_lunch: false,
    serves_dinner: false,
    readings_per_service: 3,
    cooler_max_f: '41.0',
    freezer_max_f: '0.0',
    cook_min_f: '165.0',
    reheat_min_f: '165.0',
    hot_hold_min_f: '140.0',
    cold_hold_max_f: '41.0',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [showMonitoringConfig, setShowMonitoringConfig] = useState(false);
  const [showThresholds, setShowThresholds] = useState(false);

  useEffect(() => {
    if (outlet) {
      setFormData({
        id: outlet.id,
        name: outlet.name || '',
        full_name: outlet.full_name || '',
        outlet_type: outlet.outlet_type || 'Production Kitchen',
        is_active: outlet.is_active ?? true,
        // Daily monitoring configuration
        daily_monitoring_enabled: outlet.daily_monitoring_enabled ?? false,
        cooler_count: outlet.cooler_count ?? 0,
        freezer_count: outlet.freezer_count ?? 0,
        has_cooking: outlet.has_cooking ?? false,
        has_cooling: outlet.has_cooling ?? false,
        has_thawing: outlet.has_thawing ?? false,
        has_hot_buffet: outlet.has_hot_buffet ?? false,
        has_cold_buffet: outlet.has_cold_buffet ?? false,
        serves_breakfast: outlet.serves_breakfast ?? false,
        serves_lunch: outlet.serves_lunch ?? false,
        serves_dinner: outlet.serves_dinner ?? false,
        readings_per_service: outlet.readings_per_service ?? 3,
        cooler_max_f: outlet.cooler_max_f ?? '41.0',
        freezer_max_f: outlet.freezer_max_f ?? '0.0',
        cook_min_f: outlet.cook_min_f ?? '165.0',
        reheat_min_f: outlet.reheat_min_f ?? '165.0',
        hot_hold_min_f: outlet.hot_hold_min_f ?? '140.0',
        cold_hold_max_f: outlet.cold_hold_max_f ?? '41.0',
      });
      // Auto-expand monitoring section if enabled
      if (outlet.daily_monitoring_enabled) {
        setShowMonitoringConfig(true);
      }
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

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Check if any monitoring features are configured
  const hasMonitoringConfig = formData.cooler_count > 0 ||
    formData.freezer_count > 0 ||
    formData.has_cooking ||
    formData.has_cooling ||
    formData.has_thawing;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container modal-lg" onClick={(e) => e.stopPropagation()}>
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

          {/* Basic Info Section */}
          <div className="form-section">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="outlet-name">
                  Name (tag) <span className="required">*</span>
                </label>
                <input
                  id="outlet-name"
                  type="text"
                  className="input"
                  value={formData.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  placeholder="MK, Toro, LaHa"
                  maxLength={50}
                  required
                />
                <span className="form-help">Short name used as tag/pill</span>
              </div>

              <div className="form-group flex-2">
                <label htmlFor="outlet-full-name">Full Name</label>
                <input
                  id="outlet-full-name"
                  type="text"
                  className="input"
                  value={formData.full_name}
                  onChange={(e) => updateField('full_name', e.target.value)}
                  placeholder="Main Kitchen"
                  maxLength={255}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="outlet-type">Type</label>
                <select
                  id="outlet-type"
                  className="input"
                  value={formData.outlet_type}
                  onChange={(e) => updateField('outlet_type', e.target.value)}
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
                    onChange={(e) => updateField('is_active', e.target.checked)}
                  />
                  <span>Active</span>
                </label>
              </div>
            </div>
          </div>

          {/* Daily Monitoring Section */}
          <div className="form-section collapsible">
            <button
              type="button"
              className="section-toggle"
              onClick={() => setShowMonitoringConfig(!showMonitoringConfig)}
            >
              <div className="section-toggle-left">
                <Thermometer size={18} />
                <span>Daily Monitoring Configuration</span>
                {formData.daily_monitoring_enabled && (
                  <span className="badge badge-green">Enabled</span>
                )}
                {!formData.daily_monitoring_enabled && hasMonitoringConfig && (
                  <span className="badge badge-yellow">Configured but disabled</span>
                )}
              </div>
              {showMonitoringConfig ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>

            {showMonitoringConfig && (
              <div className="section-content">
                {/* Master Toggle */}
                <div className="form-group">
                  <label className="checkbox-label toggle-primary">
                    <input
                      type="checkbox"
                      checked={formData.daily_monitoring_enabled}
                      onChange={(e) => updateField('daily_monitoring_enabled', e.target.checked)}
                    />
                    <span>Enable Daily Monitoring for this outlet</span>
                  </label>
                  <span className="form-help">
                    When enabled, this outlet will appear in the Daily Logs module
                  </span>
                </div>

                {/* Equipment Counts */}
                <div className="config-subsection">
                  <h4>Equipment Counts</h4>
                  <p className="subsection-help">
                    How many coolers and freezers need daily temperature checks?
                  </p>
                  <div className="form-row compact">
                    <div className="form-group">
                      <label>Coolers / Refrigerators</label>
                      <input
                        type="number"
                        className="input input-narrow"
                        value={formData.cooler_count}
                        onChange={(e) => updateField('cooler_count', parseInt(e.target.value) || 0)}
                        min="0"
                        max="20"
                      />
                    </div>
                    <div className="form-group">
                      <label>Freezers</label>
                      <input
                        type="number"
                        className="input input-narrow"
                        value={formData.freezer_count}
                        onChange={(e) => updateField('freezer_count', parseInt(e.target.value) || 0)}
                        min="0"
                        max="20"
                      />
                    </div>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="config-subsection">
                  <h4>Capabilities</h4>
                  <p className="subsection-help">
                    Which daily worksheet sections apply to this outlet?
                  </p>
                  <div className="checkbox-grid">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.has_cooking}
                        onChange={(e) => updateField('has_cooking', e.target.checked)}
                      />
                      <span>Cooking / Reheating</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.has_cooling}
                        onChange={(e) => updateField('has_cooling', e.target.checked)}
                      />
                      <span>Cooling Records</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.has_thawing}
                        onChange={(e) => updateField('has_thawing', e.target.checked)}
                      />
                      <span>Thawing Records</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.has_hot_buffet}
                        onChange={(e) => updateField('has_hot_buffet', e.target.checked)}
                      />
                      <span>Hot Buffet / Display</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={formData.has_cold_buffet}
                        onChange={(e) => updateField('has_cold_buffet', e.target.checked)}
                      />
                      <span>Cold Buffet / Display</span>
                    </label>
                  </div>
                </div>

                {/* Meal Periods */}
                {formData.has_cooking && (
                  <div className="config-subsection">
                    <h4>Meal Periods</h4>
                    <p className="subsection-help">
                      Which services require cook/reheat temperature logging?
                    </p>
                    <div className="form-row compact">
                      <div className="checkbox-group-inline">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={formData.serves_breakfast}
                            onChange={(e) => updateField('serves_breakfast', e.target.checked)}
                          />
                          <span>Breakfast</span>
                        </label>
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={formData.serves_lunch}
                            onChange={(e) => updateField('serves_lunch', e.target.checked)}
                          />
                          <span>Lunch</span>
                        </label>
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={formData.serves_dinner}
                            onChange={(e) => updateField('serves_dinner', e.target.checked)}
                          />
                          <span>Dinner</span>
                        </label>
                      </div>
                      <div className="form-group">
                        <label>Min readings per service</label>
                        <input
                          type="number"
                          className="input input-narrow"
                          value={formData.readings_per_service}
                          onChange={(e) => updateField('readings_per_service', parseInt(e.target.value) || 3)}
                          min="1"
                          max="10"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Temperature Thresholds */}
                <div className="config-subsection">
                  <button
                    type="button"
                    className="subsection-toggle"
                    onClick={() => setShowThresholds(!showThresholds)}
                  >
                    <span>Temperature Thresholds</span>
                    <span className="toggle-hint">
                      {showThresholds ? 'Hide' : 'Show defaults'}
                    </span>
                  </button>

                  {showThresholds && (
                    <div className="thresholds-grid">
                      <div className="threshold-item">
                        <label>Cooler max</label>
                        <div className="threshold-input">
                          <input
                            type="number"
                            step="0.1"
                            className="input input-narrow"
                            value={formData.cooler_max_f}
                            onChange={(e) => updateField('cooler_max_f', e.target.value)}
                          />
                          <span className="unit">°F</span>
                        </div>
                      </div>
                      <div className="threshold-item">
                        <label>Freezer max</label>
                        <div className="threshold-input">
                          <input
                            type="number"
                            step="0.1"
                            className="input input-narrow"
                            value={formData.freezer_max_f}
                            onChange={(e) => updateField('freezer_max_f', e.target.value)}
                          />
                          <span className="unit">°F</span>
                        </div>
                      </div>
                      <div className="threshold-item">
                        <label>Cook min</label>
                        <div className="threshold-input">
                          <input
                            type="number"
                            step="0.1"
                            className="input input-narrow"
                            value={formData.cook_min_f}
                            onChange={(e) => updateField('cook_min_f', e.target.value)}
                          />
                          <span className="unit">°F</span>
                        </div>
                      </div>
                      <div className="threshold-item">
                        <label>Reheat min</label>
                        <div className="threshold-input">
                          <input
                            type="number"
                            step="0.1"
                            className="input input-narrow"
                            value={formData.reheat_min_f}
                            onChange={(e) => updateField('reheat_min_f', e.target.value)}
                          />
                          <span className="unit">°F</span>
                        </div>
                      </div>
                      <div className="threshold-item">
                        <label>Hot hold min</label>
                        <div className="threshold-input">
                          <input
                            type="number"
                            step="0.1"
                            className="input input-narrow"
                            value={formData.hot_hold_min_f}
                            onChange={(e) => updateField('hot_hold_min_f', e.target.value)}
                          />
                          <span className="unit">°F</span>
                        </div>
                      </div>
                      <div className="threshold-item">
                        <label>Cold hold max</label>
                        <div className="threshold-input">
                          <input
                            type="number"
                            step="0.1"
                            className="input input-narrow"
                            value={formData.cold_hold_max_f}
                            onChange={(e) => updateField('cold_hold_max_f', e.target.value)}
                          />
                          <span className="unit">°F</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
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
