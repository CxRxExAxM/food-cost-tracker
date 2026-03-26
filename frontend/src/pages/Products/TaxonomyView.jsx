import { useState, useEffect, useCallback } from 'react';
import axios from '../../lib/axios';
import { useToast } from '../../contexts/ToastContext';
import './TaxonomyView.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

// Attribute labels for display
const ATTRIBUTE_LABELS = {
  variety: 'Variety',
  form: 'Form',
  prep: 'Prep',
  cut_size: 'Cut Size',
  cut: 'Cut',
  bone: 'Bone',
  skin: 'Skin',
  grade: 'Grade',
  state: 'State',
};

// Editable attributes list
const EDITABLE_ATTRS = ['variety', 'form', 'prep', 'cut_size', 'cut', 'bone', 'skin', 'grade', 'state'];

function TaxonomyView() {
  const toast = useToast();

  // Data state
  const [baseIngredients, setBaseIngredients] = useState([]);
  const [categories, setCategories] = useState([]);
  const [attributeValues, setAttributeValues] = useState({});
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [attributeFilters, setAttributeFilters] = useState({});

  // Expansion state (tracks both base and variant expansion)
  const [expandedBases, setExpandedBases] = useState(new Set());
  const [expandedVariants, setExpandedVariants] = useState(new Set());

  // Common products cache (loaded on demand)
  const [commonProductsCache, setCommonProductsCache] = useState({});
  const [loadingVariants, setLoadingVariants] = useState(new Set());

  // Editing state
  const [editingVariant, setEditingVariant] = useState(null);
  const [editForm, setEditForm] = useState({});

  // Add variant modal
  const [addVariantBase, setAddVariantBase] = useState(null);
  const [newVariantForm, setNewVariantForm] = useState({ display_name: '' });

  // Merge mode
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedForMerge, setSelectedForMerge] = useState([]);
  const [mergeBaseId, setMergeBaseId] = useState(null);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    fetchTaxonomyData();
  }, [debouncedSearch, categoryFilter]);

  useEffect(() => {
    fetchCategories();
    fetchAttributeValues();
  }, []);

  const fetchTaxonomyData = async () => {
    try {
      setLoading(true);
      const params = {
        limit: 200,
        include_counts: true,
        ...(debouncedSearch && { search: debouncedSearch }),
        ...(categoryFilter && { category: categoryFilter }),
      };
      const response = await axios.get(`${API_URL}/taxonomy/base-ingredients/with-variants`, { params });
      setBaseIngredients(response.data);

      // Auto-expand if searching
      if (debouncedSearch) {
        setExpandedBases(new Set(response.data.map(b => b.id)));
      }
    } catch (error) {
      console.error('Error fetching taxonomy data:', error);
      toast.error('Failed to load taxonomy data');
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/taxonomy/base-ingredients/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchAttributeValues = async () => {
    try {
      const response = await axios.get(`${API_URL}/taxonomy/variants/attribute-values`);
      setAttributeValues(response.data);
    } catch (error) {
      console.error('Error fetching attribute values:', error);
    }
  };

  // Fetch common products for a variant (on expand)
  const fetchCommonProducts = useCallback(async (variantId) => {
    if (commonProductsCache[variantId]) return;

    setLoadingVariants(prev => new Set([...prev, variantId]));
    try {
      const response = await axios.get(`${API_URL}/taxonomy/variants/${variantId}/common-products`);
      setCommonProductsCache(prev => ({
        ...prev,
        [variantId]: response.data
      }));
    } catch (error) {
      console.error('Error fetching common products:', error);
      toast.error('Failed to load linked products');
    } finally {
      setLoadingVariants(prev => {
        const next = new Set(prev);
        next.delete(variantId);
        return next;
      });
    }
  }, [commonProductsCache, toast]);

  const toggleBaseExpanded = (baseId) => {
    setExpandedBases(prev => {
      const next = new Set(prev);
      if (next.has(baseId)) {
        next.delete(baseId);
      } else {
        next.add(baseId);
      }
      return next;
    });
  };

  const toggleVariantExpanded = (variantId) => {
    setExpandedVariants(prev => {
      const next = new Set(prev);
      if (next.has(variantId)) {
        next.delete(variantId);
      } else {
        next.add(variantId);
        // Fetch common products when expanding
        fetchCommonProducts(variantId);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedBases(new Set(baseIngredients.map(b => b.id)));
  };

  const collapseAll = () => {
    setExpandedBases(new Set());
    setExpandedVariants(new Set());
  };

  // Filter variants by attribute filters
  const filterVariants = (variants) => {
    if (Object.keys(attributeFilters).length === 0) {
      return variants;
    }

    return variants.filter(variant => {
      return Object.entries(attributeFilters).every(([attr, value]) => {
        if (!value) return true;
        return variant[attr] === value;
      });
    });
  };

  // Get variant attribute badges
  const getVariantBadges = (variant) => {
    const badges = [];
    const attrs = ['variety', 'form', 'cut', 'bone', 'skin', 'prep', 'cut_size', 'grade', 'state'];

    attrs.forEach(attr => {
      if (variant[attr]) {
        badges.push({ attr, value: variant[attr] });
      }
    });

    return badges;
  };

  // Count total variants (after filtering)
  const getTotalVariantCount = () => {
    return baseIngredients.reduce((sum, base) => {
      return sum + filterVariants(base.variants || []).length;
    }, 0);
  };

  // Check if any attribute filters are active
  const hasActiveFilters = Object.values(attributeFilters).some(v => v);

  const clearAttributeFilters = () => {
    setAttributeFilters({});
  };

  // === Editing Functions ===
  const startEditing = (variant, e) => {
    e.stopPropagation();
    setEditingVariant(variant.id);
    setEditForm({
      display_name: variant.display_name,
      ...EDITABLE_ATTRS.reduce((acc, attr) => {
        acc[attr] = variant[attr] || '';
        return acc;
      }, {})
    });
  };

  const cancelEditing = () => {
    setEditingVariant(null);
    setEditForm({});
  };

  const saveVariantEdit = async () => {
    try {
      const updates = {};
      if (editForm.display_name) updates.display_name = editForm.display_name;
      EDITABLE_ATTRS.forEach(attr => {
        if (editForm[attr] !== undefined) {
          updates[attr] = editForm[attr] || null;
        }
      });

      await axios.patch(`${API_URL}/taxonomy/variants/${editingVariant}`, updates);
      toast.success('Variant updated');
      setEditingVariant(null);
      setEditForm({});
      fetchTaxonomyData();
    } catch (error) {
      console.error('Error updating variant:', error);
      toast.error('Failed to update variant');
    }
  };

  // === Add Variant Functions ===
  const openAddVariant = (base, e) => {
    e.stopPropagation();
    setAddVariantBase(base);
    setNewVariantForm({
      display_name: base.name,
      ...EDITABLE_ATTRS.reduce((acc, attr) => {
        acc[attr] = '';
        return acc;
      }, {})
    });
  };

  const closeAddVariant = () => {
    setAddVariantBase(null);
    setNewVariantForm({ display_name: '' });
  };

  const createVariant = async () => {
    if (!newVariantForm.display_name.trim()) {
      toast.error('Display name is required');
      return;
    }

    try {
      const payload = {
        base_ingredient_id: addVariantBase.id,
        display_name: newVariantForm.display_name,
        ...EDITABLE_ATTRS.reduce((acc, attr) => {
          acc[attr] = newVariantForm[attr] || null;
          return acc;
        }, {})
      };

      await axios.post(`${API_URL}/taxonomy/variants`, payload);
      toast.success('Variant created');
      closeAddVariant();
      fetchTaxonomyData();
    } catch (error) {
      console.error('Error creating variant:', error);
      toast.error('Failed to create variant');
    }
  };

  // === Merge Functions ===
  const toggleMergeMode = () => {
    setMergeMode(!mergeMode);
    setSelectedForMerge([]);
    setMergeBaseId(null);
  };

  const toggleMergeSelection = (variant, baseId, e) => {
    e.stopPropagation();

    // Can only merge variants from the same base
    if (mergeBaseId && mergeBaseId !== baseId) {
      toast.error('Can only merge variants from the same base ingredient');
      return;
    }

    setSelectedForMerge(prev => {
      if (prev.includes(variant.id)) {
        const next = prev.filter(id => id !== variant.id);
        if (next.length === 0) setMergeBaseId(null);
        return next;
      } else {
        if (!mergeBaseId) setMergeBaseId(baseId);
        return [...prev, variant.id];
      }
    });
  };

  const executeMerge = async () => {
    if (selectedForMerge.length < 2) {
      toast.error('Select at least 2 variants to merge');
      return;
    }

    // Use first selected as the "keep" variant
    const keepId = selectedForMerge[0];
    const mergeIds = selectedForMerge.slice(1);

    try {
      const response = await axios.post(`${API_URL}/taxonomy/variants/merge`, {
        keep_variant_id: keepId,
        merge_variant_ids: mergeIds
      });

      toast.success(`Merged ${response.data.merged_count} variants, updated ${response.data.products_updated} products`);
      setMergeMode(false);
      setSelectedForMerge([]);
      setMergeBaseId(null);
      fetchTaxonomyData();
    } catch (error) {
      console.error('Error merging variants:', error);
      toast.error('Failed to merge variants');
    }
  };

  // Format price for display
  const formatPrice = (price) => {
    if (price == null) return '-';
    return `$${parseFloat(price).toFixed(2)}`;
  };

  return (
    <div className="taxonomy-view-container">
      {/* Filters Row */}
      <div className="taxonomy-filters">
        <input
          type="text"
          placeholder="Search ingredients..."
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

        <div className="expand-controls">
          <button onClick={expandAll} className="btn-expand" title="Expand all">
            ⊞ Expand
          </button>
          <button onClick={collapseAll} className="btn-collapse" title="Collapse all">
            ⊟ Collapse
          </button>
          <button
            onClick={toggleMergeMode}
            className={`btn-merge ${mergeMode ? 'active' : ''}`}
            title="Merge duplicates"
          >
            ⊕ Merge
          </button>
        </div>
      </div>

      {/* Merge Bar */}
      {mergeMode && (
        <div className="merge-bar">
          <span className="merge-info">
            Select variants to merge ({selectedForMerge.length} selected)
          </span>
          {selectedForMerge.length >= 2 && (
            <button onClick={executeMerge} className="btn-execute-merge">
              Merge Selected
            </button>
          )}
          <button onClick={toggleMergeMode} className="btn-cancel-merge">
            Cancel
          </button>
        </div>
      )}

      {/* Attribute Filters */}
      <div className="attribute-filters">
        <span className="attribute-filters-label">Filter by attribute:</span>
        {['variety', 'form', 'prep', 'state', 'cut', 'bone', 'skin', 'grade'].map(attr => (
          attributeValues[attr]?.length > 0 && (
            <select
              key={attr}
              value={attributeFilters[attr] || ''}
              onChange={(e) => setAttributeFilters(prev => ({
                ...prev,
                [attr]: e.target.value
              }))}
              className="attribute-filter-select"
            >
              <option value="">{ATTRIBUTE_LABELS[attr]}</option>
              {attributeValues[attr].map(val => (
                <option key={val} value={val}>{val}</option>
              ))}
            </select>
          )
        ))}
        {hasActiveFilters && (
          <button onClick={clearAttributeFilters} className="btn-clear-filters">
            Clear Filters
          </button>
        )}
      </div>

      {/* Stats Bar */}
      <div className="taxonomy-stats">
        <span>{baseIngredients.length} base ingredients</span>
        <span className="stat-separator">•</span>
        <span>{getTotalVariantCount()} variants</span>
        {hasActiveFilters && (
          <>
            <span className="stat-separator">•</span>
            <span className="filtered-indicator">Filtered</span>
          </>
        )}
      </div>

      {/* Tree View */}
      {loading ? (
        <div className="loading">Loading taxonomy...</div>
      ) : baseIngredients.length === 0 ? (
        <div className="empty-state">No ingredients found</div>
      ) : (
        <div className="taxonomy-tree">
          {baseIngredients.map(base => {
            const filteredVariants = filterVariants(base.variants || []);
            const isExpanded = expandedBases.has(base.id);
            const variantCount = filteredVariants.length;

            // Skip bases with no variants after filtering (if filters active)
            if (hasActiveFilters && variantCount === 0) {
              return null;
            }

            return (
              <div key={base.id} className="base-ingredient-group">
                {/* Base Ingredient Row */}
                <div
                  className={`base-ingredient-row ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => toggleBaseExpanded(base.id)}
                >
                  <span className="expand-icon">
                    {isExpanded ? '▼' : '▶'}
                  </span>
                  <span className="base-name">{base.name}</span>
                  <span className="variant-count">
                    {variantCount} variant{variantCount !== 1 ? 's' : ''}
                  </span>
                  {base.category && (
                    <span className="base-category">{base.category}</span>
                  )}
                  <button
                    className="btn-add-variant"
                    onClick={(e) => openAddVariant(base, e)}
                    title="Add variant"
                  >
                    +
                  </button>
                </div>

                {/* Variants */}
                {isExpanded && (
                  <div className="variants-container">
                    {filteredVariants.length === 0 ? (
                      <div className="no-variants">No variants match filters</div>
                    ) : (
                      filteredVariants.map(variant => {
                        const isVariantExpanded = expandedVariants.has(variant.id);
                        const isEditing = editingVariant === variant.id;
                        const commonProducts = commonProductsCache[variant.id] || [];
                        const isLoadingProducts = loadingVariants.has(variant.id);
                        const isSelectedForMerge = selectedForMerge.includes(variant.id);
                        const hasProducts = variant.common_product_count > 0;

                        return (
                          <div key={variant.id} className="variant-group">
                            {/* Variant Row */}
                            <div
                              className={`variant-row ${isVariantExpanded ? 'expanded' : ''} ${isSelectedForMerge ? 'selected-merge' : ''}`}
                              onClick={() => hasProducts && toggleVariantExpanded(variant.id)}
                            >
                              {mergeMode ? (
                                <input
                                  type="checkbox"
                                  checked={isSelectedForMerge}
                                  onChange={(e) => toggleMergeSelection(variant, base.id, e)}
                                  className="merge-checkbox"
                                  onClick={(e) => e.stopPropagation()}
                                />
                              ) : (
                                <span className="variant-indent">
                                  {hasProducts ? (isVariantExpanded ? '▼' : '▶') : '•'}
                                </span>
                              )}

                              {isEditing ? (
                                <input
                                  type="text"
                                  value={editForm.display_name}
                                  onChange={(e) => setEditForm(prev => ({ ...prev, display_name: e.target.value }))}
                                  className="edit-input edit-name"
                                  onClick={(e) => e.stopPropagation()}
                                />
                              ) : (
                                <span className="variant-display-name">
                                  {variant.display_name}
                                </span>
                              )}

                              <div className="variant-badges">
                                {getVariantBadges(variant).map(({ attr, value }) => (
                                  <span
                                    key={attr}
                                    className={`variant-badge badge-${attr}`}
                                    title={ATTRIBUTE_LABELS[attr]}
                                  >
                                    {value}
                                  </span>
                                ))}
                              </div>

                              {/* Usage counts */}
                              <div className="variant-counts">
                                {variant.common_product_count > 0 && (
                                  <span className="count-badge count-products" title="Common products">
                                    {variant.common_product_count} CP
                                  </span>
                                )}
                                {variant.linked_product_count > 0 && (
                                  <span className="count-badge count-skus" title="Linked vendor SKUs">
                                    {variant.linked_product_count} SKU
                                  </span>
                                )}
                                {variant.recipe_count > 0 && (
                                  <span className="count-badge count-recipes" title="Used in recipes">
                                    {variant.recipe_count} recipe{variant.recipe_count !== 1 ? 's' : ''}
                                  </span>
                                )}
                              </div>

                              {/* Edit/Action buttons */}
                              {!mergeMode && (
                                <div className="variant-actions">
                                  {isEditing ? (
                                    <>
                                      <button onClick={saveVariantEdit} className="btn-save" title="Save">✓</button>
                                      <button onClick={cancelEditing} className="btn-cancel" title="Cancel">✕</button>
                                    </>
                                  ) : (
                                    <button
                                      onClick={(e) => startEditing(variant, e)}
                                      className="btn-edit"
                                      title="Edit"
                                    >
                                      ✎
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>

                            {/* Edit Form (expanded inline) */}
                            {isEditing && (
                              <div className="variant-edit-form">
                                <div className="edit-attrs">
                                  {EDITABLE_ATTRS.map(attr => (
                                    <div key={attr} className="edit-attr-field">
                                      <label>{ATTRIBUTE_LABELS[attr]}</label>
                                      <input
                                        type="text"
                                        value={editForm[attr] || ''}
                                        onChange={(e) => setEditForm(prev => ({ ...prev, [attr]: e.target.value }))}
                                        placeholder={ATTRIBUTE_LABELS[attr]}
                                        list={`attr-${attr}-options`}
                                      />
                                      {attributeValues[attr]?.length > 0 && (
                                        <datalist id={`attr-${attr}-options`}>
                                          {attributeValues[attr].map(val => (
                                            <option key={val} value={val} />
                                          ))}
                                        </datalist>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Common Products (3rd level) */}
                            {isVariantExpanded && (
                              <div className="common-products-container">
                                {isLoadingProducts ? (
                                  <div className="loading-products">Loading products...</div>
                                ) : commonProducts.length === 0 ? (
                                  <div className="no-products">No common products linked</div>
                                ) : (
                                  commonProducts.map(cp => (
                                    <div key={cp.id} className="common-product-group">
                                      <div className="common-product-row">
                                        <span className="cp-indent">├─</span>
                                        <span className="cp-name">{cp.common_name}</span>
                                        {cp.unit_name && (
                                          <span className="cp-unit">({cp.unit_name})</span>
                                        )}
                                        <span className="cp-linked-count">
                                          {cp.linked_count} SKU{cp.linked_count !== 1 ? 's' : ''}
                                        </span>
                                      </div>

                                      {/* Linked Vendor Products (4th level) */}
                                      {cp.linked_products?.length > 0 && (
                                        <div className="linked-products">
                                          {cp.linked_products.map(product => (
                                            <div key={product.distributor_product_id} className="linked-product-row">
                                              <span className="lp-indent">│  └─</span>
                                              <span className="lp-vendor">{product.distributor_name}</span>
                                              <span className="lp-description">{product.product_name}</span>
                                              {(product.pack || product.size) && (
                                                <span className="lp-pack">
                                                  {product.pack && `${product.pack}x`}{product.size}{product.unit_name && ` ${product.unit_name}`}
                                                </span>
                                              )}
                                              <span className="lp-price">{formatPrice(product.latest_price)}</span>
                                              {product.distributor_sku && (
                                                <span className="lp-code">#{product.distributor_sku}</span>
                                              )}
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  ))
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add Variant Modal */}
      {addVariantBase && (
        <div className="modal-overlay" onClick={closeAddVariant}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Add Variant to {addVariantBase.name}</h3>

            <div className="form-field">
              <label>Display Name *</label>
              <input
                type="text"
                value={newVariantForm.display_name}
                onChange={(e) => setNewVariantForm(prev => ({ ...prev, display_name: e.target.value }))}
                placeholder="e.g., Diced Carrot 1/4&quot;"
              />
            </div>

            <div className="form-grid">
              {EDITABLE_ATTRS.map(attr => (
                <div key={attr} className="form-field">
                  <label>{ATTRIBUTE_LABELS[attr]}</label>
                  <input
                    type="text"
                    value={newVariantForm[attr] || ''}
                    onChange={(e) => setNewVariantForm(prev => ({ ...prev, [attr]: e.target.value }))}
                    placeholder={ATTRIBUTE_LABELS[attr]}
                    list={`new-attr-${attr}-options`}
                  />
                  {attributeValues[attr]?.length > 0 && (
                    <datalist id={`new-attr-${attr}-options`}>
                      {attributeValues[attr].map(val => (
                        <option key={val} value={val} />
                      ))}
                    </datalist>
                  )}
                </div>
              ))}
            </div>

            <div className="modal-actions">
              <button onClick={closeAddVariant} className="btn-secondary">Cancel</button>
              <button onClick={createVariant} className="btn-primary">Create Variant</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TaxonomyView;
