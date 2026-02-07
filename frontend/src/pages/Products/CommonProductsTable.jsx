import { useState, useEffect, useCallback } from 'react';
import axios from '../../lib/axios';
import { useToast } from '../../contexts/ToastContext';
import MergeCommonProductsModal from './MergeCommonProductsModal';
import './CommonProducts.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

// Allergen definitions with abbreviations
const ALLERGENS = [
  { key: 'allergen_gluten', label: 'Gluten', abbr: 'G' },
  { key: 'allergen_dairy', label: 'Dairy', abbr: 'D' },
  { key: 'allergen_egg', label: 'Egg', abbr: 'E' },
  { key: 'allergen_fish', label: 'Fish', abbr: 'Fi' },
  { key: 'allergen_crustation', label: 'Crustacean', abbr: 'Cr' },
  { key: 'allergen_mollusk', label: 'Mollusk', abbr: 'Mo' },
  { key: 'allergen_tree_nuts', label: 'Tree Nuts', abbr: 'TN' },
  { key: 'allergen_peanuts', label: 'Peanuts', abbr: 'P' },
  { key: 'allergen_soy', label: 'Soy', abbr: 'So' },
  { key: 'allergen_sesame', label: 'Sesame', abbr: 'Se' },
  { key: 'allergen_mustard', label: 'Mustard', abbr: 'Mu' },
  { key: 'allergen_celery', label: 'Celery', abbr: 'Ce' },
  { key: 'allergen_lupin', label: 'Lupin', abbr: 'Lu' },
  { key: 'allergen_sulphur_dioxide', label: 'Sulphites', abbr: 'Su' },
];

const DIETARY = [
  { key: 'allergen_vegan', label: 'Vegan', abbr: 'VN' },
  { key: 'allergen_vegetarian', label: 'Vegetarian', abbr: 'VG' },
];

function CommonProductsTable() {
  const toast = useToast();
  // Data state
  const [commonProducts, setCommonProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [allergenFilter, setAllergenFilter] = useState('');

  // Multi-select
  const [selectedIds, setSelectedIds] = useState([]);

  // Inline editing
  const [editingCell, setEditingCell] = useState(null); // { id, field }
  const [editValue, setEditValue] = useState('');

  // Saving state for optimistic updates
  const [pendingSaves, setPendingSaves] = useState(new Set());

  // Merge modal
  const [showMergeModal, setShowMergeModal] = useState(false);

  // Linked products modal
  const [linkedProductsModal, setLinkedProductsModal] = useState(null);
  const [linkedProductsData, setLinkedProductsData] = useState(null);
  const [loadingLinkedProducts, setLoadingLinkedProducts] = useState(false);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    fetchCommonProducts();
  }, [debouncedSearch, categoryFilter, allergenFilter]);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCommonProducts = async () => {
    try {
      setLoading(true);
      const params = {
        limit: 1000,
        include_linked_count: true,
        ...(debouncedSearch && { search: debouncedSearch }),
        ...(categoryFilter && { category: categoryFilter }),
        ...(allergenFilter && { allergen: allergenFilter }),
      };
      const response = await axios.get(`${API_URL}/common-products`, { params });
      setCommonProducts(response.data);
    } catch (error) {
      console.error('Error fetching common products:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/common-products/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  // Inline editing handlers
  const startCellEdit = (id, field, currentValue) => {
    setEditingCell({ id, field });
    setEditValue(currentValue ?? '');
  };

  const cancelCellEdit = () => {
    setEditingCell(null);
    setEditValue('');
  };

  const handleCellSave = async (id, field) => {
    const oldProduct = commonProducts.find(p => p.id === id);
    const oldValue = oldProduct?.[field];

    // Don't save if value hasn't changed
    if (editValue === oldValue) {
      cancelCellEdit();
      return;
    }

    // Optimistic update
    setCommonProducts(prev =>
      prev.map(p =>
        p.id === id ? { ...p, [field]: editValue || null } : p
      )
    );
    setPendingSaves(prev => new Set(prev).add(id));
    cancelCellEdit();

    try {
      await axios.patch(`${API_URL}/common-products/${id}`, {
        [field]: editValue || null
      });

      // Refresh categories if category was changed
      if (field === 'category') {
        fetchCategories();
      }
    } catch (error) {
      console.error('Error updating common product:', error);
      // Revert on error
      setCommonProducts(prev =>
        prev.map(p =>
          p.id === id ? { ...p, [field]: oldValue } : p
        )
      );
      toast.error('Failed to save changes');
    } finally {
      setPendingSaves(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleCellKeyDown = (e, id, field) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      cancelCellEdit();
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCellSave(id, field);
      return;
    }

    if (e.key === 'Tab') {
      e.preventDefault();
      handleCellSave(id, field).then(() => {
        // Move to next editable field
        const currentIndex = commonProducts.findIndex(p => p.id === id);
        if (field === 'common_name') {
          // Move to category
          startCellEdit(id, 'category', commonProducts[currentIndex]?.category);
        } else if (field === 'category' && !e.shiftKey) {
          // Move to next row's name
          const nextProduct = commonProducts[currentIndex + 1];
          if (nextProduct) {
            startCellEdit(nextProduct.id, 'common_name', nextProduct.common_name);
          }
        } else if (field === 'category' && e.shiftKey) {
          // Move back to name
          startCellEdit(id, 'common_name', commonProducts[currentIndex]?.common_name);
        }
      });
    }
  };

  // Allergen toggle handler
  const handleAllergenToggle = async (id, allergenKey) => {
    const product = commonProducts.find(p => p.id === id);
    const newValue = !product[allergenKey];

    // Optimistic update
    setCommonProducts(prev =>
      prev.map(p =>
        p.id === id ? { ...p, [allergenKey]: newValue } : p
      )
    );

    try {
      await axios.patch(`${API_URL}/common-products/${id}`, {
        [allergenKey]: newValue
      });
    } catch (error) {
      console.error('Error updating allergen:', error);
      // Revert on error
      setCommonProducts(prev =>
        prev.map(p =>
          p.id === id ? { ...p, [allergenKey]: !newValue } : p
        )
      );
      toast.error('Failed to update allergen');
    }
  };

  // Multi-select handlers
  const toggleSelection = (id) => {
    setSelectedIds(prev =>
      prev.includes(id)
        ? prev.filter(x => x !== id)
        : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === commonProducts.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(commonProducts.map(p => p.id));
    }
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  // Get all allergen/dietary definitions combined
  const getAllAllergenDefs = () => [...ALLERGENS, ...DIETARY];

  // Handle viewing linked products
  const handleViewLinkedProducts = async (product) => {
    setLinkedProductsModal(product);
    setLoadingLinkedProducts(true);

    try {
      const response = await axios.get(`${API_URL}/common-products/${product.id}/mapped-products`);
      setLinkedProductsData(response.data);
    } catch (error) {
      console.error('Error fetching linked products:', error);
    } finally {
      setLoadingLinkedProducts(false);
    }
  };

  // Handle merge completion
  const handleMergeComplete = () => {
    setShowMergeModal(false);
    setSelectedIds([]);
    fetchCommonProducts();
  };

  // Render editable cell
  const renderEditableCell = (product, field, displayValue, className = '') => {
    const isEditing = editingCell?.id === product.id && editingCell?.field === field;
    const isPending = pendingSaves.has(product.id);

    if (isEditing) {
      if (field === 'category') {
        return (
          <div className="category-edit-wrapper">
            <input
              type="text"
              list={`categories-${product.id}`}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => handleCellSave(product.id, field)}
              onKeyDown={(e) => handleCellKeyDown(e, product.id, field)}
              className="inline-edit-input"
              autoFocus
              placeholder="Select or type..."
            />
            <datalist id={`categories-${product.id}`}>
              {categories.map(cat => (
                <option key={cat} value={cat} />
              ))}
            </datalist>
          </div>
        );
      }

      return (
        <input
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={() => handleCellSave(product.id, field)}
          onKeyDown={(e) => handleCellKeyDown(e, product.id, field)}
          className="inline-edit-input"
          autoFocus
        />
      );
    }

    return (
      <span
        className={`editable-cell ${className} ${isPending ? 'saving' : ''}`}
        onClick={() => startCellEdit(product.id, field, displayValue)}
        title="Click to edit"
      >
        {displayValue ?? '-'}
      </span>
    );
  };

  return (
    <div className="common-products-container">
      {/* Filters Row */}
      <div className="common-products-filters">
        <input
          type="text"
          placeholder="Search common products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="filter-select"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <select
          value={allergenFilter}
          onChange={(e) => setAllergenFilter(e.target.value)}
          className="filter-select"
        >
          <option value="">All Allergens</option>
          <optgroup label="Allergens">
            {ALLERGENS.map(a => (
              <option key={a.key} value={a.key}>{a.label}</option>
            ))}
          </optgroup>
          <optgroup label="Dietary">
            {DIETARY.map(a => (
              <option key={a.key} value={a.key}>{a.label}</option>
            ))}
          </optgroup>
        </select>
      </div>

      {/* Selection Bar */}
      {selectedIds.length > 0 && (
        <div className="selection-bar">
          <span className="selection-count">
            Selected: {selectedIds.length}
          </span>
          <div className="selection-actions">
            <button
              className="btn-merge"
              onClick={() => setShowMergeModal(true)}
              disabled={selectedIds.length < 2}
            >
              Merge Selected
            </button>
            <button
              className="btn-clear-selection"
              onClick={clearSelection}
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="loading">Loading common products...</div>
      ) : commonProducts.length === 0 ? (
        <div className="empty-state">No common products found</div>
      ) : (
        <div className="table-container">
          <table className="common-products-table">
            <thead>
              <tr>
                <th className="checkbox-col">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === commonProducts.length && commonProducts.length > 0}
                    onChange={toggleSelectAll}
                    title="Select all"
                  />
                </th>
                <th className="name-header">Name</th>
                <th className="allergens-header">Allergens</th>
                <th className="dietary-header">Dietary</th>
                <th className="category-header">Category</th>
                <th className="text-center linked-header">Linked</th>
              </tr>
            </thead>
            <tbody>
              {commonProducts.map((product) => (
                <tr
                  key={product.id}
                  className={selectedIds.includes(product.id) ? 'selected' : ''}
                >
                  <td className="checkbox-col">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(product.id)}
                      onChange={() => toggleSelection(product.id)}
                    />
                  </td>
                  <td className="name-cell">
                    {renderEditableCell(product, 'common_name', product.common_name)}
                  </td>
                  <td className="allergens-cell">
                    <div className="allergen-grid-inline">
                      {ALLERGENS.map(allergen => (
                        <span
                          key={allergen.key}
                          className={`allergen-pill ${product[allergen.key] ? 'checked' : ''}`}
                          onClick={() => handleAllergenToggle(product.id, allergen.key)}
                        >
                          {allergen.label}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="dietary-cell">
                    <div className="dietary-grid-inline">
                      {DIETARY.map(dietary => (
                        <span
                          key={dietary.key}
                          className={`dietary-pill ${product[dietary.key] ? 'checked' : ''}`}
                          onClick={() => handleAllergenToggle(product.id, dietary.key)}
                        >
                          {dietary.label}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="category-cell">
                    {renderEditableCell(product, 'category', product.category)}
                  </td>
                  <td className="text-center linked-cell">
                    <button
                      className="linked-count-btn"
                      onClick={() => handleViewLinkedProducts(product)}
                      title="View linked products"
                    >
                      {product.linked_products_count || 0}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Merge Modal */}
      {showMergeModal && (
        <MergeCommonProductsModal
          selectedProducts={commonProducts.filter(p => selectedIds.includes(p.id))}
          onClose={() => setShowMergeModal(false)}
          onMergeComplete={handleMergeComplete}
        />
      )}

      {/* Linked Products Modal */}
      {linkedProductsModal && (
        <div className="modal-overlay" onClick={() => setLinkedProductsModal(null)}>
          <div className="modal-content linked-products-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Linked Products</h2>
              <button className="modal-close" onClick={() => setLinkedProductsModal(null)}>×</button>
            </div>
            <div className="modal-body">
              <div className="linked-modal-product-name">
                {linkedProductsModal.common_name}
              </div>

              {loadingLinkedProducts ? (
                <div className="loading-message">Loading linked products...</div>
              ) : !linkedProductsData ? (
                <div className="empty-message">Failed to load linked products</div>
              ) : linkedProductsData.total_count === 0 ? (
                <div className="empty-state">
                  <p>No products linked to this common product yet.</p>
                </div>
              ) : (
                <div className="linked-products-list">
                  {Object.entries(linkedProductsData.products_by_outlet).map(([outletName, products]) => (
                    <div key={outletName} className="outlet-group">
                      <h3 className="outlet-group-title">{outletName}</h3>
                      {products.map(product => (
                        <div key={product.id} className="mapped-product-card">
                          <div className="mapped-product-info">
                            <div className="mapped-product-name">{product.name}</div>
                            {product.brand && <div className="mapped-product-brand">{product.brand}</div>}
                            <div className="mapped-product-meta">
                              {product.distributor_name && <span>{product.distributor_name}</span>}
                              {product.pack && product.size && product.unit_abbreviation && (
                                <span> · {product.pack}pk × {product.size}{product.unit_abbreviation}</span>
                              )}
                            </div>
                          </div>
                          <div className="mapped-product-pricing">
                            {product.case_price != null ? (
                              <>
                                <div className="mapped-price-case">${product.case_price.toFixed(2)}/cs</div>
                                {product.unit_price != null && (
                                  <div className="mapped-price-unit">
                                    ${product.unit_price.toFixed(2)}/{product.unit_abbreviation || 'unit'}
                                  </div>
                                )}
                              </>
                            ) : (
                              <div className="mapped-price-none">No price</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-done" onClick={() => setLinkedProductsModal(null)}>Done</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CommonProductsTable;
