import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Container, Plus, Pencil, Trash2, ChevronDown, ChevronRight, Search, X } from 'lucide-react';
import Navigation from '../../components/Navigation';
import UnitSelect from '../../components/UnitSelect';
import axios from '../../lib/axios';
import './Vessels.css';

function Vessels({ embedded = false }) {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states
  const [showVesselModal, setShowVesselModal] = useState(false);
  const [editingVessel, setEditingVessel] = useState(null);
  const [showCapacityModal, setShowCapacityModal] = useState(false);
  const [capacityVessel, setCapacityVessel] = useState(null);
  const [editingCapacity, setEditingCapacity] = useState(null);

  // Expanded vessel (showing capacities)
  const [expandedVesselId, setExpandedVesselId] = useState(null);

  // Common products for capacity modal
  const [commonProducts, setCommonProducts] = useState([]);

  useEffect(() => {
    loadVessels();
    loadCommonProducts();
  }, []);

  const loadVessels = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/vessels');
      setVessels(response.data.vessels || []);
      setError(null);
    } catch (err) {
      console.error('Error loading vessels:', err);
      setError('Failed to load vessels');
    } finally {
      setLoading(false);
    }
  };

  const loadCommonProducts = async () => {
    try {
      const response = await axios.get('/common-products?limit=500');
      // API returns array directly, not { products: [] }
      setCommonProducts(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Error loading common products:', err);
    }
  };

  const loadVesselDetails = async (vesselId) => {
    try {
      const response = await axios.get(`/vessels/${vesselId}`);
      // Update the vessel in the list with full details
      setVessels(prev => prev.map(v =>
        v.id === vesselId ? { ...v, ...response.data } : v
      ));
    } catch (err) {
      console.error('Error loading vessel details:', err);
    }
  };

  const toggleVesselExpansion = async (vesselId) => {
    if (expandedVesselId === vesselId) {
      setExpandedVesselId(null);
    } else {
      setExpandedVesselId(vesselId);
      // Load capacities if not already loaded
      const vessel = vessels.find(v => v.id === vesselId);
      if (!vessel.capacities) {
        await loadVesselDetails(vesselId);
      }
    }
  };

  const handleDeleteVessel = async (vesselId) => {
    if (!confirm('Are you sure you want to delete this vessel?')) return;

    try {
      await axios.delete(`/vessels/${vesselId}`);
      loadVessels();
    } catch (err) {
      console.error('Error deleting vessel:', err);
      setError('Failed to delete vessel');
    }
  };

  const handleDeleteCapacity = async (vesselId, capacityId) => {
    if (!confirm('Remove this product capacity?')) return;

    try {
      await axios.delete(`/vessels/${vesselId}/capacities/${capacityId}`);
      await loadVesselDetails(vesselId);
    } catch (err) {
      console.error('Error deleting capacity:', err);
      setError('Failed to delete capacity');
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <Navigation />
        <div className="vessels-loading">Loading vessels...</div>
      </div>
    );
  }

  return (
    <div className={`page-container ${embedded ? 'embedded' : ''}`}>
      {!embedded && <Navigation />}

      <div className="vessels-container">
        <div className="vessels-header">
          <div className="vessels-header-content">
            <Container size={32} />
            <div>
              <h1>Vessels</h1>
              <p className="vessels-subtitle">
                Manage serving vessels and their product-specific capacities
              </p>
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={() => {
              setEditingVessel(null);
              setShowVesselModal(true);
            }}
          >
            <Plus size={20} />
            Add Vessel
          </button>
        </div>

        {error && (
          <div className="error-message">{error}</div>
        )}

        {vessels.length === 0 ? (
          <div className="vessels-empty">
            <Container size={48} strokeWidth={1} />
            <h3>No vessels yet</h3>
            <p>Add vessels like "Chafing Dish" or "Small Bowl" to use in banquet prep items.</p>
            <button
              className="btn-primary"
              onClick={() => {
                setEditingVessel(null);
                setShowVesselModal(true);
              }}
            >
              <Plus size={20} />
              Add Your First Vessel
            </button>
          </div>
        ) : (
          <div className="vessels-list">
            {vessels.map(vessel => (
              <div key={vessel.id} className="vessel-card">
                <div
                  className="vessel-header"
                  onClick={() => toggleVesselExpansion(vessel.id)}
                >
                  <div className="vessel-expand-icon">
                    {expandedVesselId === vessel.id ? (
                      <ChevronDown size={20} />
                    ) : (
                      <ChevronRight size={20} />
                    )}
                  </div>
                  <div className="vessel-info">
                    <h3>{vessel.name}</h3>
                    <span className="vessel-capacity">
                      Default: {vessel.default_capacity || '—'} {vessel.default_unit_abbr || ''}
                    </span>
                    <span className="vessel-capacity-count">
                      {vessel.capacity_count || 0} product-specific capacities
                    </span>
                  </div>
                  <div className="vessel-actions" onClick={e => e.stopPropagation()}>
                    <button
                      className="btn-icon"
                      onClick={() => {
                        setEditingVessel(vessel);
                        setShowVesselModal(true);
                      }}
                      title="Edit vessel"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      className="btn-icon btn-icon-danger"
                      onClick={() => handleDeleteVessel(vessel.id)}
                      title="Delete vessel"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {expandedVesselId === vessel.id && (
                  <div className="vessel-capacities">
                    <div className="capacities-header">
                      <h4>Product Capacities</h4>
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => {
                          setCapacityVessel(vessel);
                          setEditingCapacity(null);
                          setShowCapacityModal(true);
                        }}
                      >
                        <Plus size={16} />
                        Add Capacity
                      </button>
                    </div>

                    {(!vessel.capacities || vessel.capacities.length === 0) ? (
                      <p className="no-capacities">
                        No product-specific capacities. The default capacity will be used.
                      </p>
                    ) : (
                      <div className="capacities-list">
                        {vessel.capacities.map(cap => (
                          <div key={cap.id} className="capacity-item">
                            <div className="capacity-product">
                              <span className="capacity-product-name">{cap.product_name}</span>
                              {cap.product_category && (
                                <span className="capacity-product-category">{cap.product_category}</span>
                              )}
                            </div>
                            <div className="capacity-value">
                              {cap.capacity} {cap.unit_abbr || ''}
                            </div>
                            {cap.notes && (
                              <div className="capacity-notes">{cap.notes}</div>
                            )}
                            <div className="capacity-actions">
                              <button
                                className="btn-icon btn-icon-sm"
                                onClick={() => {
                                  setCapacityVessel(vessel);
                                  setEditingCapacity(cap);
                                  setShowCapacityModal(true);
                                }}
                                title="Edit capacity"
                              >
                                <Pencil size={14} />
                              </button>
                              <button
                                className="btn-icon btn-icon-sm btn-icon-danger"
                                onClick={() => handleDeleteCapacity(vessel.id, cap.id)}
                                title="Remove capacity"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Vessel Modal */}
      {showVesselModal && (
        <VesselModal
          vessel={editingVessel}
          onClose={() => setShowVesselModal(false)}
          onSaved={() => {
            setShowVesselModal(false);
            loadVessels();
          }}
        />
      )}

      {/* Capacity Modal */}
      {showCapacityModal && capacityVessel && (
        <CapacityModal
          vessel={capacityVessel}
          capacity={editingCapacity}
          commonProducts={commonProducts}
          onClose={() => setShowCapacityModal(false)}
          onSaved={() => {
            setShowCapacityModal(false);
            loadVesselDetails(capacityVessel.id);
          }}
        />
      )}
    </div>
  );
}


// Vessel Create/Edit Modal
function VesselModal({ vessel, onClose, onSaved }) {
  const [formData, setFormData] = useState({
    name: vessel?.name || '',
    default_capacity: vessel?.default_capacity || '',
    default_unit_id: vessel?.default_unit_id || null
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
      setError('Please enter a vessel name');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formData.name,
        default_capacity: formData.default_capacity ? parseFloat(formData.default_capacity) : null,
        default_unit_id: formData.default_unit_id || null
      };

      if (vessel) {
        await axios.patch(`/vessels/${vessel.id}`, payload);
      } else {
        await axios.post('/vessels', payload);
      }

      onSaved();
    } catch (err) {
      console.error('Error saving vessel:', err);
      setError(err.response?.data?.detail || 'Failed to save vessel');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{vessel ? 'Edit Vessel' : 'Add Vessel'}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label>Vessel Name *</label>
              <input
                type="text"
                name="name"
                className="form-input"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Chafing Dish, Small Bowl"
                required
                autoFocus
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Default Capacity</label>
                <input
                  type="number"
                  name="default_capacity"
                  className="form-input"
                  value={formData.default_capacity}
                  onChange={handleChange}
                  placeholder="2.0"
                  step="0.0001"
                  min="0"
                />
              </div>

              <div className="form-group">
                <label>Unit</label>
                <UnitSelect
                  value={formData.default_unit_id}
                  onChange={handleChange}
                  name="default_unit_id"
                />
              </div>
            </div>

            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-2)' }}>
              You can add product-specific capacities after creating the vessel.
            </p>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : (vessel ? 'Save Changes' : 'Add Vessel')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// Capacity Create/Edit Modal
function CapacityModal({ vessel, capacity, commonProducts, onClose, onSaved }) {
  const [formData, setFormData] = useState({
    common_product_id: capacity?.common_product_id || null,
    capacity: capacity?.capacity || '',
    unit_id: capacity?.unit_id || null,
    notes: capacity?.notes || ''
  });
  const [selectedProduct, setSelectedProduct] = useState(
    capacity ? { id: capacity.common_product_id, common_name: capacity.product_name } : null
  );
  const [productSearch, setProductSearch] = useState('');
  const [saving, setSaving] = useState(false);

  // Filter products based on search
  const filteredProducts = commonProducts.filter(p =>
    p.common_name?.toLowerCase().includes(productSearch.toLowerCase()) ||
    p.category?.toLowerCase().includes(productSearch.toLowerCase())
  );
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setFormData(prev => ({ ...prev, common_product_id: product.id }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.common_product_id) {
      setError('Please select a product');
      return;
    }

    if (!formData.capacity) {
      setError('Please enter a capacity');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        common_product_id: formData.common_product_id,
        capacity: parseFloat(formData.capacity),
        unit_id: formData.unit_id || null,
        notes: formData.notes || null
      };

      if (capacity) {
        await axios.patch(`/vessels/${vessel.id}/capacities/${capacity.id}`, {
          capacity: payload.capacity,
          unit_id: payload.unit_id,
          notes: payload.notes
        });
      } else {
        await axios.post(`/vessels/${vessel.id}/capacities`, payload);
      }

      onSaved();
    } catch (err) {
      console.error('Error saving capacity:', err);
      setError(err.response?.data?.detail || 'Failed to save capacity');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-content-lg" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{capacity ? 'Edit Capacity' : 'Add Product Capacity'}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            <p style={{ marginBottom: 'var(--space-3)', color: 'var(--text-secondary)' }}>
              Set how many of this product fit in a {vessel.name}
            </p>

            {/* Product Selection */}
            <div className="form-group">
              <label>Product *</label>
              {selectedProduct ? (
                <div className="selected-product">
                  <span>{selectedProduct.common_name}</span>
                  {!capacity && (
                    <button
                      type="button"
                      className="btn-icon btn-icon-sm"
                      onClick={() => {
                        setSelectedProduct(null);
                        setFormData(prev => ({ ...prev, common_product_id: null }));
                      }}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <div className="search-input-wrapper">
                    <Search size={16} />
                    <input
                      type="text"
                      className="form-input"
                      value={productSearch}
                      onChange={e => setProductSearch(e.target.value)}
                      placeholder="Search products..."
                      autoFocus
                    />
                  </div>
                  <div className="product-search-results">
                    {filteredProducts.slice(0, 10).map(product => (
                      <div
                        key={product.id}
                        className="product-search-item"
                        onClick={() => handleSelectProduct(product)}
                      >
                        <span className="product-name">{product.common_name}</span>
                        {product.category && (
                          <span className="product-category">{product.category}</span>
                        )}
                      </div>
                    ))}
                    {filteredProducts.length === 0 && productSearch && (
                      <div className="no-results">No products found</div>
                    )}
                  </div>
                </>
              )}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Capacity *</label>
                <input
                  type="number"
                  name="capacity"
                  className="form-input"
                  value={formData.capacity}
                  onChange={handleChange}
                  placeholder="e.g., 18"
                  step="0.01"
                  min="0"
                  required
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

            <div className="form-group">
              <label>Notes (optional)</label>
              <input
                type="text"
                name="notes"
                className="form-input"
                value={formData.notes}
                onChange={handleChange}
                placeholder="e.g., Stacked single layer"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : (capacity ? 'Save Changes' : 'Add Capacity')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Vessels;
