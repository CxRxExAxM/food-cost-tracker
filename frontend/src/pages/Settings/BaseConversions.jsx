import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Scale, Plus, Pencil, Trash2, Info, RefreshCw } from 'lucide-react';
import Navigation from '../../components/Navigation';
import UnitSelect from '../../components/UnitSelect';
import axios from '../../lib/axios';
import './BaseConversions.css';

function BaseConversions({ embedded = false }) {
  const { currentOutlet } = useAuth();

  const [conversions, setConversions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [filterType, setFilterType] = useState('all'); // all, weight, volume, custom

  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [editingConversion, setEditingConversion] = useState(null);

  // Units for the form
  const [units, setUnits] = useState([]);

  useEffect(() => {
    loadConversions();
    loadUnits();
  }, [currentOutlet]);

  const loadConversions = async () => {
    try {
      setLoading(true);
      const params = currentOutlet ? { outlet_id: currentOutlet.id } : {};
      const response = await axios.get('/base-conversions', { params });
      setConversions(response.data.conversions || []);
      setError(null);
    } catch (err) {
      console.error('Error loading conversions:', err);
      setError('Failed to load conversions');
    } finally {
      setLoading(false);
    }
  };

  const loadUnits = async () => {
    try {
      const response = await axios.get('/units');
      setUnits(response.data.units || response.data || []);
    } catch (err) {
      console.error('Error loading units:', err);
    }
  };

  const handleDelete = async (conversionId) => {
    if (!confirm('Delete this conversion override? The system default will be used instead.')) return;

    try {
      await axios.delete(`/base-conversions/${conversionId}`);
      loadConversions();
    } catch (err) {
      console.error('Error deleting conversion:', err);
      setError(err.response?.data?.detail || 'Failed to delete conversion');
    }
  };

  // Group conversions by type
  const groupedConversions = conversions.reduce((acc, conv) => {
    const type = conv.from_unit_type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(conv);
    return acc;
  }, {});

  // Filter conversions
  const filteredGroups = filterType === 'all'
    ? groupedConversions
    : { [filterType]: groupedConversions[filterType] || [] };

  const getScopeLabel = (conv) => {
    if (conv.scope === 'system') return 'System';
    if (conv.scope === 'outlet') return conv.outlet_name || 'Outlet';
    return 'Organization';
  };

  const getScopeBadgeClass = (scope) => {
    switch (scope) {
      case 'system': return 'scope-badge-system';
      case 'outlet': return 'scope-badge-outlet';
      default: return 'scope-badge-org';
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <Navigation />
        <div className="conversions-loading">Loading conversions...</div>
      </div>
    );
  }

  return (
    <div className={`page-container ${embedded ? 'embedded' : ''}`}>
      {!embedded && <Navigation />}

      <div className="conversions-container">
        <div className="conversions-header">
          <div className="conversions-header-content">
            <Scale size={32} />
            <div>
              <h1>Unit Conversions</h1>
              <p className="conversions-subtitle">
                Manage standard unit conversions (OZ to LB, GAL to QT, etc.)
              </p>
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={() => {
              setEditingConversion(null);
              setShowModal(true);
            }}
          >
            <Plus size={20} />
            Add Override
          </button>
        </div>

        {error && (
          <div className="error-message">{error}</div>
        )}

        {/* Info Box */}
        <div className="info-box">
          <Info size={18} />
          <div>
            <strong>How conversions work:</strong>
            <p>
              System defaults provide standard conversions (16 OZ = 1 LB). You can create
              organization or outlet overrides if needed. Product-specific conversions
              (e.g., 1 ribeye = 6 OZ) are managed in Common Products.
            </p>
          </div>
        </div>

        {/* Type Filter */}
        <div className="conversions-filter">
          <button
            className={`filter-btn ${filterType === 'all' ? 'active' : ''}`}
            onClick={() => setFilterType('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filterType === 'weight' ? 'active' : ''}`}
            onClick={() => setFilterType('weight')}
          >
            Weight
          </button>
          <button
            className={`filter-btn ${filterType === 'volume' ? 'active' : ''}`}
            onClick={() => setFilterType('volume')}
          >
            Volume
          </button>
        </div>

        {/* Conversions List */}
        {Object.entries(filteredGroups).map(([type, typeConversions]) => (
          typeConversions && typeConversions.length > 0 && (
            <div key={type} className="conversions-group">
              <h2 className="group-title">{type.charAt(0).toUpperCase() + type.slice(1)}</h2>
              <div className="conversions-table">
                <div className="table-header">
                  <div className="col-from">From</div>
                  <div className="col-arrow"></div>
                  <div className="col-to">To</div>
                  <div className="col-factor">Factor</div>
                  <div className="col-scope">Scope</div>
                  <div className="col-actions"></div>
                </div>
                {typeConversions.map(conv => (
                  <div key={conv.id} className="table-row">
                    <div className="col-from">
                      <span className="unit-abbr">{conv.from_unit_abbr}</span>
                      <span className="unit-name">{conv.from_unit_name}</span>
                    </div>
                    <div className="col-arrow">=</div>
                    <div className="col-to">
                      <span className="unit-factor">{parseFloat(conv.conversion_factor).toFixed(6).replace(/\.?0+$/, '')}</span>
                      <span className="unit-abbr">{conv.to_unit_abbr}</span>
                    </div>
                    <div className="col-factor">
                      <span className="factor-display">
                        1 {conv.from_unit_abbr} = {parseFloat(conv.conversion_factor).toFixed(6).replace(/\.?0+$/, '')} {conv.to_unit_abbr}
                      </span>
                    </div>
                    <div className="col-scope">
                      <span className={`scope-badge ${getScopeBadgeClass(conv.scope)}`}>
                        {getScopeLabel(conv)}
                      </span>
                    </div>
                    <div className="col-actions">
                      {conv.scope !== 'system' ? (
                        <>
                          <button
                            className="btn-icon btn-icon-sm"
                            onClick={() => {
                              setEditingConversion(conv);
                              setShowModal(true);
                            }}
                            title="Edit conversion"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            className="btn-icon btn-icon-sm btn-icon-danger"
                            onClick={() => handleDelete(conv.id)}
                            title="Delete override"
                          >
                            <Trash2 size={14} />
                          </button>
                        </>
                      ) : (
                        <button
                          className="btn-icon btn-icon-sm"
                          onClick={() => {
                            // Create an override based on this system default
                            setEditingConversion({
                              ...conv,
                              id: null, // Will create new
                              scope: 'organization'
                            });
                            setShowModal(true);
                          }}
                          title="Create override"
                        >
                          <RefreshCw size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        ))}

        {conversions.length === 0 && (
          <div className="conversions-empty">
            <Scale size={48} strokeWidth={1} />
            <h3>No conversions found</h3>
            <p>Run the database migration to seed system default conversions.</p>
          </div>
        )}
      </div>

      {/* Conversion Modal */}
      {showModal && (
        <ConversionModal
          conversion={editingConversion}
          units={units}
          currentOutlet={currentOutlet}
          onClose={() => setShowModal(false)}
          onSaved={() => {
            setShowModal(false);
            loadConversions();
          }}
        />
      )}
    </div>
  );
}


// Conversion Create/Edit Modal
function ConversionModal({ conversion, units, currentOutlet, onClose, onSaved }) {
  const [formData, setFormData] = useState({
    from_unit_id: conversion?.from_unit_id || null,
    to_unit_id: conversion?.to_unit_id || null,
    conversion_factor: conversion?.conversion_factor || '',
    outlet_id: conversion?.outlet_id || null,
    notes: conversion?.notes || ''
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const isEditing = conversion?.id;
  const isOverride = conversion && !conversion.id; // Creating override from system default

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.from_unit_id || !formData.to_unit_id) {
      setError('Please select both units');
      return;
    }

    if (!formData.conversion_factor || parseFloat(formData.conversion_factor) <= 0) {
      setError('Please enter a valid conversion factor');
      return;
    }

    if (formData.from_unit_id === formData.to_unit_id) {
      setError('From and to units must be different');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        from_unit_id: parseInt(formData.from_unit_id),
        to_unit_id: parseInt(formData.to_unit_id),
        conversion_factor: parseFloat(formData.conversion_factor),
        outlet_id: formData.outlet_id ? parseInt(formData.outlet_id) : null,
        notes: formData.notes || null
      };

      if (isEditing) {
        await axios.patch(`/base-conversions/${conversion.id}`, {
          conversion_factor: payload.conversion_factor,
          notes: payload.notes
        });
      } else {
        await axios.post('/base-conversions', payload);
      }

      onSaved();
    } catch (err) {
      console.error('Error saving conversion:', err);
      setError(err.response?.data?.detail || 'Failed to save conversion');
    } finally {
      setSaving(false);
    }
  };

  // Group units by type for easier selection
  const unitsByType = units.reduce((acc, unit) => {
    const type = unit.unit_type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(unit);
    return acc;
  }, {});

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>
            {isEditing ? 'Edit Conversion' : isOverride ? 'Create Override' : 'Add Conversion'}
          </h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            {isOverride && (
              <div className="info-box info-box-sm">
                <Info size={16} />
                <span>Creating an organization override for this system conversion.</span>
              </div>
            )}

            <div className="form-row">
              <div className="form-group">
                <label>From Unit *</label>
                <select
                  name="from_unit_id"
                  className="form-input"
                  value={formData.from_unit_id || ''}
                  onChange={handleChange}
                  disabled={isEditing || isOverride}
                  required
                >
                  <option value="">Select unit...</option>
                  {Object.entries(unitsByType).map(([type, typeUnits]) => (
                    <optgroup key={type} label={type.charAt(0).toUpperCase() + type.slice(1)}>
                      {typeUnits.map(unit => (
                        <option key={unit.id} value={unit.id}>
                          {unit.abbreviation} - {unit.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>To Unit *</label>
                <select
                  name="to_unit_id"
                  className="form-input"
                  value={formData.to_unit_id || ''}
                  onChange={handleChange}
                  disabled={isEditing || isOverride}
                  required
                >
                  <option value="">Select unit...</option>
                  {Object.entries(unitsByType).map(([type, typeUnits]) => (
                    <optgroup key={type} label={type.charAt(0).toUpperCase() + type.slice(1)}>
                      {typeUnits.map(unit => (
                        <option key={unit.id} value={unit.id}>
                          {unit.abbreviation} - {unit.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Conversion Factor *</label>
              <input
                type="number"
                name="conversion_factor"
                className="form-input"
                value={formData.conversion_factor}
                onChange={handleChange}
                placeholder="e.g., 16 (for OZ to LB)"
                step="any"
                min="0.000001"
                required
                autoFocus={!isOverride}
              />
              <p className="form-help">
                How many "To Units" equal 1 "From Unit"
              </p>
            </div>

            {!isEditing && currentOutlet && (
              <div className="form-group">
                <label>Scope</label>
                <select
                  name="outlet_id"
                  className="form-input"
                  value={formData.outlet_id || ''}
                  onChange={handleChange}
                >
                  <option value="">Organization-wide</option>
                  <option value={currentOutlet.id}>{currentOutlet.name} only</option>
                </select>
              </div>
            )}

            <div className="form-group">
              <label>Notes (optional)</label>
              <input
                type="text"
                name="notes"
                className="form-input"
                value={formData.notes}
                onChange={handleChange}
                placeholder="e.g., Custom conversion for our recipes"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create Conversion')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default BaseConversions;
