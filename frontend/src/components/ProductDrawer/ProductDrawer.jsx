import { useState, useEffect } from 'react';
import axios from '../../lib/axios';
import { useToast } from '../../contexts/ToastContext';
import './ProductDrawer.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

// Allergen definitions with abbreviations
const ALLERGENS = [
  { key: 'allergen_gluten', label: 'Gluten', abbr: 'G' },
  { key: 'allergen_dairy', label: 'Dairy', abbr: 'D' },
  { key: 'allergen_egg', label: 'Egg', abbr: 'E' },
  { key: 'allergen_fish', label: 'Fish', abbr: 'F' },
  { key: 'allergen_crustation', label: 'Crustacean', abbr: 'Cr' },
  { key: 'allergen_mollusk', label: 'Mollusk', abbr: 'Mo' },
  { key: 'allergen_tree_nuts', label: 'Tree Nuts', abbr: 'TN' },
  { key: 'allergen_peanuts', label: 'Peanuts', abbr: 'P' },
  { key: 'allergen_soy', label: 'Soy', abbr: 'So' },
  { key: 'allergen_sesame', label: 'Sesame', abbr: 'Se' },
  { key: 'allergen_mustard', label: 'Mustard', abbr: 'Mu' },
  { key: 'allergen_celery', label: 'Celery', abbr: 'Ce' },
  { key: 'allergen_lupin', label: 'Lupin', abbr: 'L' },
  { key: 'allergen_sulphur_dioxide', label: 'Sulphites', abbr: 'Su' },
];

const DIETARY = [
  { key: 'allergen_vegan', label: 'Vegan', abbr: 'VN' },
  { key: 'allergen_vegetarian', label: 'Vegetarian', abbr: 'VG' },
];

function ProductDrawer({ productId, onClose, onProductUpdated }) {
  const toast = useToast();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('allergens');
  const [conversions, setConversions] = useState([]);
  const [units, setUnits] = useState([]);
  const [newConversion, setNewConversion] = useState({
    from_unit_id: '',
    to_unit_id: '',
    conversion_factor: '',
    notes: '',
    create_reverse: true
  });
  const [mappedProductsData, setMappedProductsData] = useState(null);
  const [selectedOutlet, setSelectedOutlet] = useState('all');
  const [loadingMappedProducts, setLoadingMappedProducts] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');

  useEffect(() => {
    if (productId) {
      fetchProduct();
      fetchConversions();
      fetchUnits();
    }
  }, [productId]);

  useEffect(() => {
    if (product && activeTab === 'mapped') {
      fetchMappedProducts();
    }
  }, [product, activeTab]);

  const fetchProduct = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/common-products/${productId}`);
      setProduct(response.data);
      setEditedName(response.data.common_name);
    } catch (error) {
      console.error('Error fetching product:', error);
      toast.error('Failed to load product');
    } finally {
      setLoading(false);
    }
  };

  const fetchConversions = async () => {
    try {
      const response = await axios.get(`${API_URL}/common-products/${productId}/conversions`);
      setConversions(response.data);
    } catch (error) {
      console.error('Error fetching conversions:', error);
    }
  };

  const fetchUnits = async () => {
    try {
      const response = await axios.get(`${API_URL}/units`);
      setUnits(response.data);
    } catch (error) {
      console.error('Error fetching units:', error);
    }
  };

  const fetchMappedProducts = async () => {
    setLoadingMappedProducts(true);
    try {
      const response = await axios.get(`${API_URL}/common-products/${productId}/mapped-products`);
      setMappedProductsData(response.data);
    } catch (error) {
      console.error('Error fetching mapped products:', error);
    } finally {
      setLoadingMappedProducts(false);
    }
  };

  const handleUpdate = async (updates) => {
    try {
      await axios.patch(`${API_URL}/common-products/${productId}`, updates);
      setProduct(prev => ({ ...prev, ...updates }));
      if (onProductUpdated) {
        onProductUpdated();
      }
    } catch (error) {
      console.error('Error updating product:', error);
      toast.error('Failed to update product');
    }
  };

  const handleToggle = (allergenKey) => {
    const newValue = !product[allergenKey];
    handleUpdate({ [allergenKey]: newValue });
  };

  const handleNameSave = async () => {
    if (editedName.trim() && editedName !== product.common_name) {
      await handleUpdate({ common_name: editedName.trim() });
    }
    setEditingName(false);
  };

  const handleCreateConversion = async () => {
    if (!newConversion.from_unit_id || !newConversion.to_unit_id || !newConversion.conversion_factor) {
      toast.warning('Please fill in all required fields');
      return;
    }

    try {
      await axios.post(`${API_URL}/common-products/${productId}/conversions`, {
        from_unit_id: parseInt(newConversion.from_unit_id),
        to_unit_id: parseInt(newConversion.to_unit_id),
        conversion_factor: parseFloat(newConversion.conversion_factor),
        notes: newConversion.notes || null,
        create_reverse: newConversion.create_reverse
      });

      fetchConversions();
      setNewConversion({
        from_unit_id: '',
        to_unit_id: '',
        conversion_factor: '',
        notes: '',
        create_reverse: true
      });
      toast.success('Conversion added');
    } catch (error) {
      console.error('Error creating conversion:', error);
      toast.error(error.response?.data?.detail || 'Failed to create conversion');
    }
  };

  const handleDeleteConversion = async (conversionId) => {
    if (!confirm('Delete this conversion?')) return;

    try {
      await axios.delete(`${API_URL}/common-products/${productId}/conversions/${conversionId}`);
      fetchConversions();
      toast.success('Conversion deleted');
    } catch (error) {
      console.error('Error deleting conversion:', error);
      toast.error('Failed to delete conversion');
    }
  };

  const handleUnmapProduct = async (productIdToUnmap) => {
    if (!confirm('Unmap this product? This will remove the connection to the common product.')) return;
    try {
      await axios.patch(`${API_URL}/products/${productIdToUnmap}/unmap`);
      fetchMappedProducts();
      toast.success('Product unmapped');
    } catch (error) {
      console.error('Error unmapping product:', error);
      toast.error('Failed to unmap product');
    }
  };

  if (loading) {
    return (
      <div className="product-drawer-overlay" onClick={onClose}>
        <div className="product-drawer" onClick={(e) => e.stopPropagation()}>
          <div className="drawer-loading">Loading...</div>
        </div>
      </div>
    );
  }

  if (!product) {
    return null;
  }

  return (
    <div className="product-drawer-overlay" onClick={onClose}>
      <div className="product-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title-section">
            {editingName ? (
              <input
                type="text"
                className="drawer-name-input"
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                onBlur={handleNameSave}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleNameSave();
                  if (e.key === 'Escape') {
                    setEditedName(product.common_name);
                    setEditingName(false);
                  }
                }}
                autoFocus
              />
            ) : (
              <h2
                className="drawer-title"
                onClick={() => setEditingName(true)}
                title="Click to edit name"
              >
                {product.common_name}
              </h2>
            )}
            {product.category && (
              <span className="drawer-category">{product.category}</span>
            )}
          </div>
          <button className="drawer-close" onClick={onClose}>×</button>
        </div>

        {/* Tab Navigation */}
        <div className="drawer-tabs">
          <button
            className={`drawer-tab ${activeTab === 'allergens' ? 'active' : ''}`}
            onClick={() => setActiveTab('allergens')}
          >
            Allergens
          </button>
          <button
            className={`drawer-tab ${activeTab === 'conversions' ? 'active' : ''}`}
            onClick={() => setActiveTab('conversions')}
          >
            Conversions
          </button>
          <button
            className={`drawer-tab ${activeTab === 'mapped' ? 'active' : ''}`}
            onClick={() => setActiveTab('mapped')}
          >
            Mapped Products
          </button>
        </div>

        {/* Tab Content */}
        <div className="drawer-content">
          {/* Allergens Tab */}
          {activeTab === 'allergens' && (
            <>
              <div className="allergen-section">
                <h3>Allergens</h3>
                <p className="section-note">Select all allergens this product contains</p>
                <div className="allergen-grid">
                  {ALLERGENS.map(allergen => (
                    <label
                      key={allergen.key}
                      className={`allergen-checkbox ${product[allergen.key] ? 'active' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={product[allergen.key] || false}
                        onChange={() => handleToggle(allergen.key)}
                      />
                      <span className="allergen-abbr">{allergen.abbr}</span>
                      <span className="allergen-label">{allergen.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="allergen-section dietary-section">
                <h3>Dietary Flags</h3>
                <p className="section-note">Mark if this product is suitable</p>
                <div className="allergen-grid dietary-grid">
                  {DIETARY.map(flag => (
                    <label
                      key={flag.key}
                      className={`allergen-checkbox dietary ${product[flag.key] ? 'active' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={product[flag.key] || false}
                        onChange={() => handleToggle(flag.key)}
                      />
                      <span className="allergen-abbr">{flag.abbr}</span>
                      <span className="allergen-label">{flag.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Conversions Tab */}
          {activeTab === 'conversions' && (
            <div className="conversions-content">
              <h3>Existing Conversions</h3>
              <div className="conversions-list">
                {conversions.length === 0 ? (
                  <p className="empty-message">No conversions defined for this product yet.</p>
                ) : (
                  conversions.map(conv => (
                    <div key={conv.id} className="conversion-item">
                      <div className="conversion-display">
                        <span className="conversion-formula">
                          1 {conv.from_unit_name} = {conv.conversion_factor} {conv.to_unit_name}
                        </span>
                        {conv.notes && <small className="conversion-notes">{conv.notes}</small>}
                      </div>
                      <button
                        className="btn-delete-conversion"
                        onClick={() => handleDeleteConversion(conv.id)}
                        title="Delete conversion"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>

              <h3 className="add-conversion-title">Add New Conversion</h3>
              <div className="conversion-form">
                <div className="form-row">
                  <div className="form-field">
                    <label>From Unit:</label>
                    <select
                      value={newConversion.from_unit_id}
                      onChange={(e) => setNewConversion({...newConversion, from_unit_id: e.target.value})}
                    >
                      <option value="">Select unit...</option>
                      {units.map(u => (
                        <option key={u.id} value={u.id}>{u.name} ({u.abbreviation})</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-field">
                    <label>To Unit:</label>
                    <select
                      value={newConversion.to_unit_id}
                      onChange={(e) => setNewConversion({...newConversion, to_unit_id: e.target.value})}
                    >
                      <option value="">Select unit...</option>
                      {units.map(u => (
                        <option key={u.id} value={u.id}>{u.name} ({u.abbreviation})</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-field">
                  <label>Conversion Factor:</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newConversion.conversion_factor}
                    onChange={(e) => setNewConversion({...newConversion, conversion_factor: e.target.value})}
                    placeholder="e.g., 5 (means 1 from unit = 5 to units)"
                  />
                  <small className="field-hint">
                    Example: If 1 ea = 5 oz, enter 5
                  </small>
                </div>

                <div className="form-field">
                  <label>Notes (optional):</label>
                  <input
                    type="text"
                    value={newConversion.notes}
                    onChange={(e) => setNewConversion({...newConversion, notes: e.target.value})}
                    placeholder="e.g., Average weight"
                  />
                </div>

                <label className="checkbox-inline">
                  <input
                    type="checkbox"
                    checked={newConversion.create_reverse}
                    onChange={(e) => setNewConversion({...newConversion, create_reverse: e.target.checked})}
                  />
                  Also create reverse conversion (recommended)
                </label>

                <button className="btn-add-conversion" onClick={handleCreateConversion}>
                  Add Conversion
                </button>
              </div>
            </div>
          )}

          {/* Mapped Products Tab */}
          {activeTab === 'mapped' && (
            <div className="mapped-products-content">
              {loadingMappedProducts ? (
                <div className="loading-message">Loading mapped products...</div>
              ) : !mappedProductsData ? (
                <div className="empty-message">Failed to load mapped products</div>
              ) : mappedProductsData.total_count === 0 ? (
                <div className="empty-state">
                  <p>No products mapped to this common product yet.</p>
                  <p className="empty-hint">Map products from the Products page to see them here.</p>
                </div>
              ) : (
                <>
                  {Object.keys(mappedProductsData.products_by_outlet).length > 1 && (
                    <div className="outlet-filter-tabs">
                      <button
                        className={`outlet-filter-btn ${selectedOutlet === 'all' ? 'active' : ''}`}
                        onClick={() => setSelectedOutlet('all')}
                      >
                        All ({mappedProductsData.total_count})
                      </button>
                      {Object.entries(mappedProductsData.products_by_outlet).map(([outletName, products]) => (
                        <button
                          key={outletName}
                          className={`outlet-filter-btn ${selectedOutlet === outletName ? 'active' : ''}`}
                          onClick={() => setSelectedOutlet(outletName)}
                        >
                          {outletName} ({products.length})
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="mapped-products-list">
                    {Object.entries(mappedProductsData.products_by_outlet)
                      .filter(([outletName]) => selectedOutlet === 'all' || selectedOutlet === outletName)
                      .map(([outletName, products]) => (
                        <div key={outletName} className="outlet-group">
                          <h3 className="outlet-group-title">{outletName}</h3>
                          {products.map(mappedProduct => (
                            <div key={mappedProduct.id} className="mapped-product-card">
                              <div className="mapped-product-info">
                                <div className="mapped-product-name">{mappedProduct.name}</div>
                                {mappedProduct.brand && (
                                  <div className="mapped-product-brand">{mappedProduct.brand}</div>
                                )}
                                <div className="mapped-product-meta">
                                  {mappedProduct.distributor_name && <span>{mappedProduct.distributor_name}</span>}
                                  {mappedProduct.pack && mappedProduct.size && mappedProduct.unit_abbreviation && (
                                    <span> • {mappedProduct.pack}pk × {mappedProduct.size}{mappedProduct.unit_abbreviation}</span>
                                  )}
                                </div>
                              </div>
                              <div className="mapped-product-pricing">
                                {mappedProduct.case_price != null ? (
                                  <>
                                    <div className="mapped-price-case">${mappedProduct.case_price.toFixed(2)}/cs</div>
                                    {mappedProduct.unit_price != null && (
                                      <div className="mapped-price-unit">
                                        ${mappedProduct.unit_price.toFixed(2)}/{mappedProduct.unit_abbreviation || 'unit'}
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <div className="mapped-price-none">No price</div>
                                )}
                              </div>
                              <button
                                className="btn-unmap"
                                onClick={() => handleUnmapProduct(mappedProduct.id)}
                                title="Unmap this product"
                              >
                                Unmap
                              </button>
                            </div>
                          ))}
                        </div>
                      ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="drawer-footer">
          <button className="btn-done" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

export default ProductDrawer;
