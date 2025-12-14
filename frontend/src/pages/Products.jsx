import { useState, useEffect } from 'react';
import axios from '../lib/axios';
import Navigation from '../components/Navigation';
import { useOutlet } from '../contexts/OutletContext';
import OutletBadge from '../components/outlets/OutletBadge';
import './Products.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

// Allergen definitions with icons and labels
const ALLERGENS = [
  { key: 'allergen_gluten', label: 'Gluten', icon: '🌾' },
  { key: 'allergen_dairy', label: 'Dairy', icon: '🥛' },
  { key: 'allergen_egg', label: 'Egg', icon: '🥚' },
  { key: 'allergen_fish', label: 'Fish', icon: '🐟' },
  { key: 'allergen_crustation', label: 'Crustacean', icon: '🦐' },
  { key: 'allergen_mollusk', label: 'Mollusk', icon: '🦪' },
  { key: 'allergen_tree_nuts', label: 'Tree Nuts', icon: '🌰' },
  { key: 'allergen_peanuts', label: 'Peanuts', icon: '🥜' },
  { key: 'allergen_soy', label: 'Soy', icon: '🫘' },
  { key: 'allergen_sesame', label: 'Sesame', icon: '⚪' },
  { key: 'allergen_mustard', label: 'Mustard', icon: '🟡' },
  { key: 'allergen_celery', label: 'Celery', icon: '🥬' },
  { key: 'allergen_lupin', label: 'Lupin', icon: '🌸' },
  { key: 'allergen_sulphur_dioxide', label: 'Sulphites', icon: '🧪' },
  { key: 'allergen_vegan', label: 'Vegan', icon: '🌱', dietary: true },
  { key: 'allergen_vegetarian', label: 'Vegetarian', icon: '🥗', dietary: true },
];

function Products() {
  const { currentOutlet, outlets } = useOutlet();
  const [products, setProducts] = useState([]);
  const [commonProducts, setCommonProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unmappedOnly, setUnmappedOnly] = useState(false);
  const [editingProductId, setEditingProductId] = useState(null);
  const [mappingInput, setMappingInput] = useState('');
  const [filteredCommonProducts, setFilteredCommonProducts] = useState([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [editingCommonProductId, setEditingCommonProductId] = useState(null);
  const [commonProductEditInput, setCommonProductEditInput] = useState('');
  const [allergenModalProduct, setAllergenModalProduct] = useState(null);
  // Upload state
  const [showUpload, setShowUpload] = useState(false);
  const [distributors, setDistributors] = useState([]);
  const [selectedDistributor, setSelectedDistributor] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split('T')[0]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  // Inline editing state
  const [units, setUnits] = useState([]);
  const [editingCell, setEditingCell] = useState(null); // { productId, field }
  const [editValue, setEditValue] = useState('');
  // Sorting state
  const [sortColumn, setSortColumn] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const [totalCount, setTotalCount] = useState(0);
  // Add new product state
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [newProduct, setNewProduct] = useState({
    name: '',
    brand: '',
    distributor_id: '',
    pack: '',
    size: '',
    unit_id: '',
    is_catch_weight: false,
    case_price: '',
    outlet_id: currentOutlet?.id && currentOutlet.id !== 'all' ? currentOutlet.id : ''
  });

  useEffect(() => {
    fetchProducts();
    fetchCommonProducts();
    fetchDistributors();
    fetchUnits();
  }, [search, unmappedOnly, sortColumn, sortDirection, currentOutlet]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const params = {
        limit: 100,
        sort_by: sortColumn,
        sort_dir: sortDirection,
        ...(search && { search }),
        ...(unmappedOnly && { unmapped_only: true }),
        // Filter by outlet if specific outlet selected (not "All Outlets")
        ...(currentOutlet && currentOutlet.id !== 'all' && { outlet_id: currentOutlet.id })
      };
      const response = await axios.get(`${API_URL}/products`, { params });
      setProducts(response.data.products);
      setTotalCount(response.data.total);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCommonProducts = async () => {
    try {
      const response = await axios.get(`${API_URL}/common-products`, { params: { limit: 1000 } });
      setCommonProducts(response.data);
    } catch (error) {
      console.error('Error fetching common products:', error);
    }
  };

  const fetchDistributors = async () => {
    try {
      const response = await axios.get(`${API_URL}/uploads/distributors`);
      setDistributors(response.data);
    } catch (error) {
      console.error('Error fetching distributors:', error);
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

  const handleFileUpload = async () => {
    if (!uploadFile || !selectedDistributor) {
      alert('Please select a distributor and file');
      return;
    }

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('distributor_code', selectedDistributor);
    formData.append('effective_date', effectiveDate);

    try {
      const response = await axios.post(`${API_URL}/uploads/csv`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadResult(response.data);
      // Refresh products list after successful upload
      if (response.data.success) {
        fetchProducts();
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadResult({
        success: false,
        message: error.response?.data?.detail || 'Upload failed',
        errors: []
      });
    } finally {
      setUploading(false);
    }
  };

  const resetUpload = () => {
    setUploadFile(null);
    setSelectedDistributor('');
    setUploadResult(null);
    setEffectiveDate(new Date().toISOString().split('T')[0]);
  };

  const handleMappingInputChange = (value) => {
    setMappingInput(value);
    if (value) {
      const filtered = commonProducts.filter(cp =>
        cp.common_name.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredCommonProducts(filtered);
      setShowAutocomplete(true);
    } else {
      setShowAutocomplete(false);
    }
  };

  const handleSelectCommonProduct = async (productId, commonProduct) => {
    try {
      await axios.patch(`${API_URL}/products/${productId}`, {
        common_product_id: commonProduct.id
      });

      // Update the local state
      setProducts(products.map(p =>
        p.id === productId
          ? { ...p, common_product_id: commonProduct.id, common_product_name: commonProduct.common_name }
          : p
      ));

      setEditingProductId(null);
      setMappingInput('');
      setShowAutocomplete(false);
    } catch (error) {
      console.error('Error mapping product:', error);
      alert('Failed to map product');
    }
  };

  const handleCreateAndMapCommonProduct = async (productId) => {
    if (!mappingInput.trim()) return;

    try {
      // Create new common product
      const createResponse = await axios.post(`${API_URL}/common-products`, {
        common_name: mappingInput.trim()
      });

      const newCommonProduct = createResponse.data;

      // Map to the product
      await axios.patch(`${API_URL}/products/${productId}`, {
        common_product_id: newCommonProduct.id
      });

      // Update local state
      setProducts(products.map(p =>
        p.id === productId
          ? { ...p, common_product_id: newCommonProduct.id, common_product_name: newCommonProduct.common_name }
          : p
      ));

      setCommonProducts([...commonProducts, newCommonProduct]);
      setEditingProductId(null);
      setMappingInput('');
      setShowAutocomplete(false);
    } catch (error) {
      console.error('Error creating common product:', error);
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert('Failed to create common product');
      }
    }
  };

  const handleUnmap = async (productId) => {
    try {
      await axios.patch(`${API_URL}/products/${productId}/unmap`);

      setProducts(products.map(p =>
        p.id === productId
          ? { ...p, common_product_id: null, common_product_name: null }
          : p
      ));
    } catch (error) {
      console.error('Error unmapping product:', error);
      alert('Failed to unmap product');
    }
  };

  const startEditing = (product) => {
    setEditingProductId(product.id);
    setMappingInput('');
    setShowAutocomplete(false);
  };

  const cancelEditing = () => {
    setEditingProductId(null);
    setMappingInput('');
    setShowAutocomplete(false);
  };

  const startEditingCommonProduct = (product) => {
    setEditingCommonProductId(product.common_product_id);
    setCommonProductEditInput(product.common_product_name);
  };

  const cancelEditingCommonProduct = () => {
    setEditingCommonProductId(null);
    setCommonProductEditInput('');
  };

  const handleUpdateCommonProduct = async (commonProductId) => {
    if (!commonProductEditInput.trim()) {
      cancelEditingCommonProduct();
      return;
    }

    try {
      await axios.patch(`${API_URL}/common-products/${commonProductId}`, {
        common_name: commonProductEditInput.trim()
      });

      // Update all products with this common_product_id
      setProducts(products.map(p =>
        p.common_product_id === commonProductId
          ? { ...p, common_product_name: commonProductEditInput.trim() }
          : p
      ));

      // Update commonProducts state
      setCommonProducts(commonProducts.map(cp =>
        cp.id === commonProductId
          ? { ...cp, common_name: commonProductEditInput.trim() }
          : cp
      ));

      cancelEditingCommonProduct();
    } catch (error) {
      console.error('Error updating common product:', error);
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert('Failed to update common product');
      }
    }
  };

  const openAllergenModal = (commonProductId) => {
    const cp = commonProducts.find(c => c.id === commonProductId);
    if (cp) {
      setAllergenModalProduct(cp);
    }
  };

  const handleUpdateAllergens = async (commonProductId, allergenUpdates) => {
    try {
      const response = await axios.patch(`${API_URL}/common-products/${commonProductId}`, allergenUpdates);

      // Update commonProducts state with full response
      setCommonProducts(commonProducts.map(cp =>
        cp.id === commonProductId ? response.data : cp
      ));

      // Update the modal product too
      setAllergenModalProduct(response.data);
    } catch (error) {
      console.error('Error updating allergens:', error);
      alert('Failed to update allergens');
    }
  };

  const getActiveAllergens = (commonProductId) => {
    const cp = commonProducts.find(c => c.id === commonProductId);
    if (!cp) return [];
    return ALLERGENS.filter(a => cp[a.key]);
  };

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : 'N/A';
  };

  const getCommonProductName = (product) => {
    if (!product.common_product_id) return null;
    // Use the common_product_name from the API response
    return product.common_product_name || 'Unknown';
  };

  // Add new product handlers
  const resetNewProduct = () => {
    setNewProduct({
      name: '',
      brand: '',
      distributor_id: '',
      pack: '',
      size: '',
      unit_id: '',
      is_catch_weight: false,
      case_price: ''
    });
  };

  const handleCreateProduct = async () => {
    if (!newProduct.name.trim()) {
      alert('Product name is required');
      return;
    }

    try {
      const productData = {
        name: newProduct.name.trim(),
        brand: newProduct.brand.trim() || null,
        pack: newProduct.pack ? parseInt(newProduct.pack) : null,
        size: newProduct.size ? parseFloat(newProduct.size) : null,
        unit_id: newProduct.unit_id ? parseInt(newProduct.unit_id) : null,
        is_catch_weight: newProduct.is_catch_weight,
        distributor_id: newProduct.distributor_id ? parseInt(newProduct.distributor_id) : null,
        case_price: newProduct.case_price ? parseFloat(newProduct.case_price) : null,
        outlet_id: newProduct.outlet_id ? parseInt(newProduct.outlet_id) : null
      };

      await axios.post(`${API_URL}/products`, productData);

      // Refresh products list and reset form
      fetchProducts();
      resetNewProduct();
      setShowAddProduct(false);
    } catch (error) {
      console.error('Error creating product:', error);
      alert('Failed to create product');
    }
  };

  // Catch weight toggle handler
  const handleToggleCatchWeight = async (product) => {
    try {
      const newValue = !product.is_catch_weight;
      await axios.patch(`${API_URL}/products/${product.id}`, {
        is_catch_weight: newValue
      });

      // Update local state
      setProducts(products.map(p =>
        p.id === product.id ? { ...p, is_catch_weight: newValue } : p
      ));
    } catch (error) {
      console.error('Error toggling catch weight:', error);
      alert('Failed to update catch weight');
    }
  };

  // Inline editing functions
  const startCellEdit = (productId, field, currentValue) => {
    setEditingCell({ productId, field });
    setEditValue(currentValue ?? '');
  };

  const cancelCellEdit = () => {
    setEditingCell(null);
    setEditValue('');
  };

  const handleCellSave = async (productId, field) => {
    try {
      let updateData = {};

      // Handle different field types
      if (field === 'unit_id') {
        updateData[field] = editValue ? parseInt(editValue) : null;
      } else if (field === 'pack') {
        updateData[field] = editValue ? parseInt(editValue) : null;
      } else if (field === 'size') {
        updateData[field] = editValue ? parseFloat(editValue) : null;
      } else {
        updateData[field] = editValue || null;
      }

      await axios.patch(`${API_URL}/products/${productId}`, updateData);

      // Update local state and recalculate unit price if needed
      setProducts(products.map(p => {
        if (p.id === productId) {
          const updated = { ...p, [field]: updateData[field] };
          // If unit changed, also update the abbreviation display
          if (field === 'unit_id') {
            const unit = units.find(u => u.id === updateData[field]);
            updated.unit_abbreviation = unit ? unit.abbreviation : null;
          }
          // Recalculate unit price if pack or size changed
          if ((field === 'pack' || field === 'size') && updated.case_price) {
            const newPack = field === 'pack' ? updateData[field] : updated.pack;
            const newSize = field === 'size' ? updateData[field] : updated.size;
            if (newPack && newSize) {
              updated.unit_price = Math.round((updated.case_price / (newPack * newSize)) * 100) / 100;
            }
          }
          return updated;
        }
        return p;
      }));

      cancelCellEdit();
    } catch (error) {
      console.error('Error updating product:', error);
      alert('Failed to update product');
    }
  };

  // Sort handler
  const handleSort = (column) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to ascending
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Render sortable header
  const renderSortableHeader = (column, label, className = '') => {
    const isActive = sortColumn === column;
    const arrow = isActive ? (sortDirection === 'asc' ? ' ▲' : ' ▼') : '';
    return (
      <th
        className={`sortable-header ${className} ${isActive ? 'active' : ''}`}
        onClick={() => handleSort(column)}
      >
        {label}{arrow}
      </th>
    );
  };

  const renderEditableCell = (product, field, displayValue, className = '') => {
    const isEditing = editingCell?.productId === product.id && editingCell?.field === field;

    if (isEditing) {
      if (field === 'unit_id') {
        return (
          <select
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => handleCellSave(product.id, field)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') cancelCellEdit();
            }}
            className="inline-edit-select"
            autoFocus
          >
            <option value="">-</option>
            {units.map(u => (
              <option key={u.id} value={u.id}>{u.abbreviation}</option>
            ))}
          </select>
        );
      }

      return (
        <input
          type={field === 'pack' || field === 'size' ? 'number' : 'text'}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={() => handleCellSave(product.id, field)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleCellSave(product.id, field);
            if (e.key === 'Escape') cancelCellEdit();
          }}
          className="inline-edit-input"
          autoFocus
          step={field === 'size' ? '0.01' : undefined}
        />
      );
    }

    // Determine the value to pass for editing
    let editStartValue = displayValue;
    if (field === 'unit_id') {
      editStartValue = product.unit_id;
    }

    return (
      <span
        className={`editable-cell ${className}`}
        onClick={() => startCellEdit(product.id, field, editStartValue)}
        title="Click to edit"
      >
        {displayValue ?? '-'}
      </span>
    );
  };

  return (
    <>
      <Navigation />
      <div className="container">
        <div className="page-header">
        <div className="header-content">
          <h1>Products</h1>
          <p>View and manage distributor products</p>
        </div>
        <button
          className={`btn-upload-toggle ${showUpload ? 'active' : ''}`}
          onClick={() => setShowUpload(!showUpload)}
        >
          {showUpload ? '✕ Close' : '📤 Import Price List'}
        </button>
      </div>

      {/* Upload Section */}
      {showUpload && (
        <div className="upload-section">
          <h3>Import Vendor Price List</h3>

          {!uploadResult ? (
            <div className="upload-form">
              <div className="upload-row">
                <div className="upload-field">
                  <label>Vendor:</label>
                  <select
                    value={selectedDistributor}
                    onChange={(e) => setSelectedDistributor(e.target.value)}
                    className="upload-select"
                  >
                    <option value="">Select vendor...</option>
                    {distributors.map(d => (
                      <option key={d.id} value={d.code}>{d.name}</option>
                    ))}
                  </select>
                </div>

                <div className="upload-field">
                  <label>Effective Date:</label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="upload-date"
                  />
                </div>
              </div>

              <div className="upload-file-area">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  id="csv-upload"
                  className="file-input"
                />
                <label htmlFor="csv-upload" className="file-label">
                  {uploadFile ? (
                    <span className="file-selected">📄 {uploadFile.name}</span>
                  ) : (
                    <span>📁 Click to select CSV or Excel file</span>
                  )}
                </label>
              </div>

              <div className="upload-actions">
                <button
                  className="btn-upload"
                  onClick={handleFileUpload}
                  disabled={!uploadFile || !selectedDistributor || uploading}
                >
                  {uploading ? 'Uploading...' : 'Upload & Import'}
                </button>
                {uploadFile && (
                  <button className="btn-clear" onClick={resetUpload}>
                    Clear
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className={`upload-result ${uploadResult.success ? 'success' : 'error'}`}>
              <div className="result-header">
                <span className="result-icon">{uploadResult.success ? '✓' : '✕'}</span>
                <span className="result-message">{uploadResult.message}</span>
              </div>

              {uploadResult.success && (
                <div className="result-stats">
                  <div className="stat">
                    <span className="stat-value">{uploadResult.rows_imported}</span>
                    <span className="stat-label">Rows Imported</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{uploadResult.new_products}</span>
                    <span className="stat-label">New Products</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{uploadResult.updated_prices}</span>
                    <span className="stat-label">Prices Updated</span>
                  </div>
                  {uploadResult.rows_failed > 0 && (
                    <div className="stat warning">
                      <span className="stat-value">{uploadResult.rows_failed}</span>
                      <span className="stat-label">Failed Rows</span>
                    </div>
                  )}
                </div>
              )}

              {uploadResult.errors && uploadResult.errors.length > 0 && (
                <div className="result-errors">
                  <h4>Errors:</h4>
                  <ul>
                    {uploadResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              <button className="btn-new-upload" onClick={resetUpload}>
                Upload Another File
              </button>
            </div>
          )}
        </div>
      )}

      <div className="filters">
        <input
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={unmappedOnly}
            onChange={(e) => setUnmappedOnly(e.target.checked)}
          />
          Show unmapped only
        </label>

        <div className="results-count">
          {!loading && (totalCount > products.length
            ? `${products.length} of ${totalCount} products`
            : `${totalCount} products`)}
        </div>

        <button
          className={`btn-add-product ${showAddProduct ? 'active' : ''}`}
          onClick={() => {
            setShowAddProduct(!showAddProduct);
            if (showAddProduct) resetNewProduct();
          }}
        >
          {showAddProduct ? '✕ Cancel' : '+ Add Product'}
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="empty-state">No products found</div>
      ) : (
        <div className="table-container">
          <table className="products-table">
            <thead>
              <tr>
                {renderSortableHeader('name', 'Product Name')}
                {renderSortableHeader('brand', 'Brand')}
                {renderSortableHeader('distributor_name', 'Distributor')}
                <th className="text-center">Outlet</th>
                {renderSortableHeader('pack', 'Pack', 'text-center')}
                {renderSortableHeader('size', 'Size', 'text-center')}
                {renderSortableHeader('unit', 'Unit', 'text-center')}
                <th className="text-center" title="Catch Weight">CW</th>
                {renderSortableHeader('case_price', 'Case Price', 'text-right')}
                {renderSortableHeader('unit_price', 'Unit Price', 'text-right')}
                {renderSortableHeader('common_product_name', 'Common Product')}
              </tr>
            </thead>
            <tbody>
              {/* Add new product row */}
              {showAddProduct && (
                <tr className="add-product-row">
                  <td>
                    <input
                      type="text"
                      value={newProduct.name}
                      onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                      placeholder="Product name *"
                      className="inline-edit-input"
                      autoFocus
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      value={newProduct.brand}
                      onChange={(e) => setNewProduct({ ...newProduct, brand: e.target.value })}
                      placeholder="Brand"
                      className="inline-edit-input"
                    />
                  </td>
                  <td>
                    <select
                      value={newProduct.distributor_id}
                      onChange={(e) => setNewProduct({ ...newProduct, distributor_id: e.target.value })}
                      className="inline-edit-select"
                    >
                      <option value="">Distributor</option>
                      {distributors.map(d => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      value={newProduct.outlet_id}
                      onChange={(e) => setNewProduct({ ...newProduct, outlet_id: e.target.value })}
                      className="inline-edit-select"
                    >
                      <option value="">Outlet *</option>
                      {outlets.filter(o => o.id !== 'all').map(outlet => (
                        <option key={outlet.id} value={outlet.id}>{outlet.name}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      value={newProduct.pack}
                      onChange={(e) => setNewProduct({ ...newProduct, pack: e.target.value })}
                      placeholder="Pack"
                      className="inline-edit-input"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={newProduct.size}
                      onChange={(e) => setNewProduct({ ...newProduct, size: e.target.value })}
                      placeholder="Size"
                      className="inline-edit-input"
                    />
                  </td>
                  <td>
                    <select
                      value={newProduct.unit_id}
                      onChange={(e) => setNewProduct({ ...newProduct, unit_id: e.target.value })}
                      className="inline-edit-select"
                    >
                      <option value="">Unit</option>
                      {units.map(u => (
                        <option key={u.id} value={u.id}>{u.abbreviation}</option>
                      ))}
                    </select>
                  </td>
                  <td className="text-center">
                    <button
                      className={`catch-weight-toggle ${newProduct.is_catch_weight ? 'active' : ''}`}
                      onClick={() => setNewProduct({ ...newProduct, is_catch_weight: !newProduct.is_catch_weight })}
                      title="Toggle catch weight"
                    >
                      {newProduct.is_catch_weight ? '⚖️' : '○'}
                    </button>
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      value={newProduct.case_price}
                      onChange={(e) => setNewProduct({ ...newProduct, case_price: e.target.value })}
                      placeholder="Case $"
                      className="inline-edit-input"
                    />
                  </td>
                  <td className="text-center text-muted">-</td>
                  <td>
                    <button className="btn-save-product" onClick={handleCreateProduct}>
                      Save
                    </button>
                  </td>
                </tr>
              )}
              {products.map((product) => (
                <tr key={product.id}>
                  <td className="product-name">{renderEditableCell(product, 'name', product.name)}</td>
                  <td className="brand-cell">{renderEditableCell(product, 'brand', product.brand)}</td>
                  <td className="distributor-cell">{product.distributor_name}</td>
                  <td className="text-center">
                    <OutletBadge outletId={product.outlet_id} />
                  </td>
                  <td className="text-center">{renderEditableCell(product, 'pack', product.pack)}</td>
                  <td className="text-center">{renderEditableCell(product, 'size', product.size)}</td>
                  <td className="text-center">{renderEditableCell(product, 'unit_id', product.unit_abbreviation)}</td>
                  <td className="text-center">
                    <button
                      className={`catch-weight-toggle ${product.is_catch_weight ? 'active' : ''}`}
                      onClick={() => handleToggleCatchWeight(product)}
                      title={product.is_catch_weight ? 'Catch Weight (click to disable)' : 'Not Catch Weight (click to enable)'}
                    >
                      {product.is_catch_weight ? '⚖️' : '○'}
                    </button>
                  </td>
                  <td className="text-right price-cell">{formatPrice(product.case_price)}</td>
                  <td className="text-right price-cell">{formatPrice(product.unit_price)}</td>
                  <td className="mapping-cell">
                    {editingProductId === product.id ? (
                      <div className="mapping-editor">
                        <input
                          type="text"
                          value={mappingInput}
                          onChange={(e) => handleMappingInputChange(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && mappingInput.trim()) {
                              handleCreateAndMapCommonProduct(product.id);
                            } else if (e.key === 'Escape') {
                              cancelEditing();
                            }
                          }}
                          placeholder="Type to search or create..."
                          className="mapping-input"
                          autoFocus
                        />

                        {showAutocomplete && filteredCommonProducts.length > 0 && (
                          <div className="autocomplete-dropdown">
                            {filteredCommonProducts.map((cp) => (
                              <div
                                key={cp.id}
                                className="autocomplete-item"
                                onClick={() => handleSelectCommonProduct(product.id, cp)}
                              >
                                {cp.common_name}
                                {cp.category && <span className="category-tag">{cp.category}</span>}
                              </div>
                            ))}
                          </div>
                        )}

                        {mappingInput && filteredCommonProducts.length === 0 && (
                          <div className="autocomplete-dropdown">
                            <div
                              className="autocomplete-item create-new"
                              onClick={() => handleCreateAndMapCommonProduct(product.id)}
                            >
                              + Create "{mappingInput}"
                            </div>
                          </div>
                        )}

                        <div className="mapping-actions">
                          <button onClick={cancelEditing} className="btn-cancel">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <div className="mapping-display">
                        {product.common_product_id ? (
                          <>
                            {editingCommonProductId === product.common_product_id ? (
                              <div className="common-product-edit">
                                <input
                                  type="text"
                                  value={commonProductEditInput}
                                  onChange={(e) => setCommonProductEditInput(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      handleUpdateCommonProduct(product.common_product_id);
                                    } else if (e.key === 'Escape') {
                                      cancelEditingCommonProduct();
                                    }
                                  }}
                                  onBlur={() => handleUpdateCommonProduct(product.common_product_id)}
                                  className="common-product-edit-input"
                                  autoFocus
                                />
                              </div>
                            ) : (
                              <div className="common-product-display">
                                <span
                                  className="common-product-badge clickable"
                                  onClick={() => startEditingCommonProduct(product)}
                                  title="Click to edit name"
                                >
                                  {getCommonProductName(product)}
                                </span>
                                <div className="allergen-icons">
                                  {getActiveAllergens(product.common_product_id).slice(0, 4).map(a => (
                                    <span key={a.key} className="allergen-icon" title={a.label}>
                                      {a.icon}
                                    </span>
                                  ))}
                                  {getActiveAllergens(product.common_product_id).length > 4 && (
                                    <span className="allergen-more">+{getActiveAllergens(product.common_product_id).length - 4}</span>
                                  )}
                                </div>
                                <button
                                  onClick={() => openAllergenModal(product.common_product_id)}
                                  className="btn-allergen"
                                  title="Manage allergens"
                                >
                                  🏷️
                                </button>
                                <button
                                  onClick={() => handleUnmap(product.id)}
                                  className="btn-unmap"
                                  title="Unmap this product"
                                >
                                  ×
                                </button>
                              </div>
                            )}
                          </>
                        ) : (
                          <button
                            onClick={() => startEditing(product)}
                            className="btn-map"
                          >
                            + Map
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Allergen Modal */}
      {allergenModalProduct && (
        <AllergenModal
          product={allergenModalProduct}
          onClose={() => setAllergenModalProduct(null)}
          onUpdate={handleUpdateAllergens}
        />
      )}
      </div>
    </>
  );
}

// Allergen Modal Component
function AllergenModal({ product, onClose, onUpdate }) {
  const allergenAllergens = ALLERGENS.filter(a => !a.dietary);
  const dietaryFlags = ALLERGENS.filter(a => a.dietary);

  const handleToggle = (allergenKey) => {
    const newValue = !product[allergenKey];
    onUpdate(product.id, { [allergenKey]: newValue });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content allergen-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Allergens & Dietary</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="allergen-product-name">{product.common_name}</div>

          <div className="allergen-section">
            <h3>Allergens</h3>
            <p className="allergen-section-note">Select all allergens this product contains</p>
            <div className="allergen-grid">
              {allergenAllergens.map(allergen => (
                <label key={allergen.key} className={`allergen-checkbox ${product[allergen.key] ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={product[allergen.key] || false}
                    onChange={() => handleToggle(allergen.key)}
                  />
                  <span className="allergen-checkbox-icon">{allergen.icon}</span>
                  <span className="allergen-checkbox-label">{allergen.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="allergen-section dietary-section">
            <h3>Dietary Flags</h3>
            <p className="allergen-section-note">Mark if this product is suitable</p>
            <div className="allergen-grid dietary-grid">
              {dietaryFlags.map(flag => (
                <label key={flag.key} className={`allergen-checkbox dietary ${product[flag.key] ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={product[flag.key] || false}
                    onChange={() => handleToggle(flag.key)}
                  />
                  <span className="allergen-checkbox-icon">{flag.icon}</span>
                  <span className="allergen-checkbox-label">{flag.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-done" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

export default Products;
