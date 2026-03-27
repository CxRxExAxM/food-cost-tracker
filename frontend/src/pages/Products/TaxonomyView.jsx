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

// Recursive component for rendering variant tree
function VariantTree({
  variants,
  baseId,
  depth,
  expandedVariants,
  toggleVariantExpanded,
  mergeMode,
  selectedForMerge,
  toggleMergeSelection,
  editingVariant,
  editForm,
  setEditForm,
  startEditing,
  saveVariantEdit,
  cancelEditing,
  openMoveModal,
  getVariantBadges,
  loadingVariants,
  commonProductsCache,
  editingCP,
  editCPName,
  setEditCPName,
  startEditingCP,
  saveCPEdit,
  cancelEditingCP,
  attributeTooltips,
  loadingTooltip,
  fetchAttributeTooltip,
  formatTooltipContent,
  formatPrice,
  attributeValues,
  openReassignModal,
  EDITABLE_ATTRS,
  ATTRIBUTE_LABELS,
}) {
  return variants.map(variant => {
    const isVariantExpanded = expandedVariants.has(variant.id);
    const isEditing = editingVariant === variant.id;
    const commonProducts = commonProductsCache[variant.id] || [];
    const isLoadingProducts = loadingVariants.has(variant.id);
    const isSelectedForMerge = selectedForMerge.includes(variant.id);
    const hasProducts = variant.common_product_count > 0;
    const hasChildren = variant.children?.length > 0;
    const canExpand = hasProducts || hasChildren;

    return (
      <div key={variant.id} className="variant-group" style={{ marginLeft: depth * 20 }}>
        {/* Variant Row */}
        <div
          className={`variant-row ${isVariantExpanded ? 'expanded' : ''} ${isSelectedForMerge ? 'selected-merge' : ''} depth-${depth}`}
          onClick={() => canExpand && toggleVariantExpanded(variant.id)}
        >
          {mergeMode ? (
            <input
              type="checkbox"
              checked={isSelectedForMerge}
              onChange={(e) => toggleMergeSelection(variant, baseId, e)}
              className="merge-checkbox"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span className="variant-indent">
              {depth > 0 && <span className="tree-line">└</span>}
              {canExpand ? (isVariantExpanded ? '▼' : '▶') : '•'}
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
            {hasChildren && (
              <span className="count-badge count-children" title="Child variants">
                {variant.children.length} sub
              </span>
            )}
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
                <>
                  <button
                    onClick={(e) => startEditing(variant, e)}
                    className="btn-edit"
                    title="Edit attributes"
                  >
                    ✎
                  </button>
                  <button
                    onClick={(e) => openMoveModal(variant, baseId, e)}
                    className="btn-move"
                    title="Move in hierarchy"
                  >
                    ↕
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Edit Form (expanded inline) */}
        {isEditing && (
          <div className="variant-edit-form" style={{ marginLeft: depth * 20 }}>
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

        {/* Child variants (recursive) */}
        {isVariantExpanded && hasChildren && (
          <VariantTree
            variants={variant.children}
            baseId={baseId}
            depth={depth + 1}
            expandedVariants={expandedVariants}
            toggleVariantExpanded={toggleVariantExpanded}
            mergeMode={mergeMode}
            selectedForMerge={selectedForMerge}
            toggleMergeSelection={toggleMergeSelection}
            editingVariant={editingVariant}
            editForm={editForm}
            setEditForm={setEditForm}
            startEditing={startEditing}
            saveVariantEdit={saveVariantEdit}
            cancelEditing={cancelEditing}
            openMoveModal={openMoveModal}
            getVariantBadges={getVariantBadges}
            loadingVariants={loadingVariants}
            commonProductsCache={commonProductsCache}
            editingCP={editingCP}
            editCPName={editCPName}
            setEditCPName={setEditCPName}
            startEditingCP={startEditingCP}
            saveCPEdit={saveCPEdit}
            cancelEditingCP={cancelEditingCP}
            attributeTooltips={attributeTooltips}
            loadingTooltip={loadingTooltip}
            fetchAttributeTooltip={fetchAttributeTooltip}
            formatTooltipContent={formatTooltipContent}
            formatPrice={formatPrice}
            attributeValues={attributeValues}
            openReassignModal={openReassignModal}
            EDITABLE_ATTRS={EDITABLE_ATTRS}
            ATTRIBUTE_LABELS={ATTRIBUTE_LABELS}
          />
        )}

        {/* Common Products */}
        {isVariantExpanded && hasProducts && (
          <div className="common-products-container" style={{ marginLeft: (depth + 1) * 20 }}>
            {isLoadingProducts ? (
              <div className="loading-products">Loading products...</div>
            ) : commonProducts.length === 0 ? (
              <div className="no-products">No common products linked</div>
            ) : (
              commonProducts.map(cp => {
                const isEditingThisCP = editingCP === cp.id;
                const tooltip = attributeTooltips[cp.id];
                const hasUnassigned = tooltip && Object.keys(tooltip.unassigned_attributes || {}).length > 0;

                return (
                  <div key={cp.id} className="common-product-group">
                    <div className={`common-product-row ${hasUnassigned ? 'has-unassigned' : ''}`}>
                      <span className="cp-indent">├─</span>

                      {isEditingThisCP ? (
                        <input
                          type="text"
                          value={editCPName}
                          onChange={(e) => setEditCPName(e.target.value)}
                          className="cp-edit-input"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveCPEdit(cp.id, variant.id);
                            if (e.key === 'Escape') cancelEditingCP();
                          }}
                        />
                      ) : (
                        <span className="cp-name">{cp.common_name}</span>
                      )}

                      {cp.unit_name && (
                        <span className="cp-unit">({cp.unit_name})</span>
                      )}
                      <span className="cp-linked-count">
                        {cp.linked_count} SKU{cp.linked_count !== 1 ? 's' : ''}
                      </span>

                      {/* Attribute info button */}
                      <button
                        className={`btn-cp-info ${hasUnassigned ? 'has-warning' : ''}`}
                        onMouseEnter={() => fetchAttributeTooltip(cp.id)}
                        title={formatTooltipContent(tooltip)}
                      >
                        {loadingTooltip === cp.id ? '...' : hasUnassigned ? '⚠' : 'ℹ'}
                      </button>

                      {/* Edit/Save/Cancel buttons */}
                      <div className="cp-actions">
                        {isEditingThisCP ? (
                          <>
                            <button
                              onClick={() => saveCPEdit(cp.id, variant.id)}
                              className="btn-save"
                              title="Save (reassigns if needed)"
                            >
                              ✓
                            </button>
                            <button
                              onClick={cancelEditingCP}
                              className="btn-cancel"
                              title="Cancel"
                            >
                              ✕
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={(e) => startEditingCP(cp, e)}
                            className="btn-edit"
                            title="Edit name"
                          >
                            ✎
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Linked Vendor Products */}
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
                            <button
                              className="btn-reassign"
                              onClick={(e) => openReassignModal(product, variant.id, e)}
                              title="Move to different common product"
                            >
                              ↗
                            </button>
                          </div>
                        ))}
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
  });
}

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

  // Common product editing
  const [editingCP, setEditingCP] = useState(null);
  const [editCPName, setEditCPName] = useState('');

  // Attribute tooltip cache
  const [attributeTooltips, setAttributeTooltips] = useState({});
  const [loadingTooltip, setLoadingTooltip] = useState(null);

  // Move variant modal
  const [movingVariant, setMovingVariant] = useState(null);
  const [moveTargetId, setMoveTargetId] = useState(null);

  // Product reassignment modal
  const [reassigningProduct, setReassigningProduct] = useState(null);
  const [cpSearchQuery, setCpSearchQuery] = useState('');
  const [cpSearchResults, setCpSearchResults] = useState([]);
  const [selectedNewCP, setSelectedNewCP] = useState(null);
  const [searchingCPs, setSearchingCPs] = useState(false);

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

  // Filter variants by attribute filters (recursive for hierarchical structure)
  const filterVariants = (variants) => {
    if (Object.keys(attributeFilters).length === 0) {
      return variants;
    }

    const filterRecursive = (variantList) => {
      return variantList.filter(variant => {
        const matchesFilter = Object.entries(attributeFilters).every(([attr, value]) => {
          if (!value) return true;
          return variant[attr] === value;
        });

        // Also filter children recursively
        if (variant.children?.length > 0) {
          variant.children = filterRecursive(variant.children);
        }

        // Keep variant if it matches OR if it has matching children
        return matchesFilter || (variant.children?.length > 0);
      });
    };

    return filterRecursive([...variants]);
  };

  // Count all variants including children
  const countVariants = (variants) => {
    return variants.reduce((count, v) => {
      return count + 1 + (v.children ? countVariants(v.children) : 0);
    }, 0);
  };

  // Get flat list of all variants for move target selection
  const getAllVariantsFlat = (variants, depth = 0) => {
    const result = [];
    variants.forEach(v => {
      result.push({ ...v, depth });
      if (v.children?.length > 0) {
        result.push(...getAllVariantsFlat(v.children, depth + 1));
      }
    });
    return result;
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

  // Count total variants (after filtering) - uses recursive count for hierarchical tree
  const getTotalVariantCount = () => {
    return baseIngredients.reduce((sum, base) => {
      return sum + countVariants(filterVariants(base.variants || []));
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

  // === Move Variant Functions ===
  const openMoveModal = (variant, baseId, e) => {
    e.stopPropagation();
    setMovingVariant({ ...variant, baseId });
    setMoveTargetId(variant.parent_variant_id || 'root');
  };

  const closeMoveModal = () => {
    setMovingVariant(null);
    setMoveTargetId(null);
  };

  const executeMove = async () => {
    if (!movingVariant) return;

    const newParentId = moveTargetId === 'root' ? null : parseInt(moveTargetId);

    // Don't move if same position
    if (newParentId === movingVariant.parent_variant_id) {
      closeMoveModal();
      return;
    }

    try {
      await axios.patch(`${API_URL}/taxonomy/variants/${movingVariant.id}/move`, {
        parent_variant_id: newParentId
      });
      toast.success('Variant moved');
      closeMoveModal();
      fetchTaxonomyData();
    } catch (error) {
      console.error('Error moving variant:', error);
      toast.error(error.response?.data?.detail || 'Failed to move variant');
    }
  };

  // === Product Reassignment Functions ===
  const openReassignModal = (product, variantId, e) => {
    e.stopPropagation();
    setReassigningProduct({ ...product, currentVariantId: variantId });
    setCpSearchQuery('');
    setCpSearchResults([]);
    setSelectedNewCP(null);
  };

  const closeReassignModal = () => {
    setReassigningProduct(null);
    setCpSearchQuery('');
    setCpSearchResults([]);
    setSelectedNewCP(null);
  };

  const searchCommonProducts = async (query) => {
    if (query.length < 2) {
      setCpSearchResults([]);
      return;
    }

    setSearchingCPs(true);
    try {
      const response = await axios.get(`${API_URL}/taxonomy/common-products/search`, {
        params: { q: query, limit: 20 }
      });
      setCpSearchResults(response.data);
    } catch (error) {
      console.error('Error searching common products:', error);
    } finally {
      setSearchingCPs(false);
    }
  };

  // Debounce CP search
  useEffect(() => {
    if (!reassigningProduct) return;

    const timer = setTimeout(() => {
      searchCommonProducts(cpSearchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [cpSearchQuery, reassigningProduct]);

  const executeReassign = async () => {
    if (!reassigningProduct || !selectedNewCP) return;

    try {
      await axios.patch(`${API_URL}/taxonomy/products/${reassigningProduct.id}/reassign`, {
        common_product_id: selectedNewCP.id
      });
      toast.success(`Moved to "${selectedNewCP.common_name}"`);

      // Clear cache for the old variant to force reload
      setCommonProductsCache(prev => {
        const next = { ...prev };
        delete next[reassigningProduct.currentVariantId];
        return next;
      });

      closeReassignModal();
      fetchTaxonomyData();
    } catch (error) {
      console.error('Error reassigning product:', error);
      toast.error(error.response?.data?.detail || 'Failed to reassign product');
    }
  };

  // === Common Product Editing Functions ===
  const startEditingCP = (cp, e) => {
    e.stopPropagation();
    setEditingCP(cp.id);
    setEditCPName(cp.common_name);
  };

  const cancelEditingCP = () => {
    setEditingCP(null);
    setEditCPName('');
  };

  const saveCPEdit = async (cpId, variantId) => {
    if (!editCPName.trim()) {
      toast.error('Name is required');
      return;
    }

    try {
      const response = await axios.patch(`${API_URL}/taxonomy/common-products/${cpId}/reparse`, {
        common_name: editCPName
      });

      if (response.data.moved) {
        toast.success(`Moved to "${response.data.variant_display_name}"`);
        // Clear cache for both old and new variant to force reload
        setCommonProductsCache(prev => {
          const next = { ...prev };
          delete next[variantId];
          delete next[response.data.variant_id];
          return next;
        });
        // Re-fetch taxonomy to update counts
        fetchTaxonomyData();
      } else {
        toast.success('Name updated');
        // Update the cache inline
        setCommonProductsCache(prev => ({
          ...prev,
          [variantId]: prev[variantId]?.map(cp =>
            cp.id === cpId ? { ...cp, common_name: editCPName } : cp
          )
        }));
      }

      setEditingCP(null);
      setEditCPName('');
    } catch (error) {
      console.error('Error updating common product:', error);
      toast.error('Failed to update');
    }
  };

  // Fetch detected attributes for tooltip
  const fetchAttributeTooltip = async (cpId) => {
    if (attributeTooltips[cpId]) return; // Already cached

    setLoadingTooltip(cpId);
    try {
      const response = await axios.get(`${API_URL}/taxonomy/common-products/${cpId}/detected-attributes`);
      setAttributeTooltips(prev => ({
        ...prev,
        [cpId]: response.data
      }));
    } catch (error) {
      console.error('Error fetching attributes:', error);
    } finally {
      setLoadingTooltip(null);
    }
  };

  // Format price for display
  const formatPrice = (price) => {
    if (price == null) return '-';
    return `$${parseFloat(price).toFixed(2)}`;
  };

  // Format attribute tooltip
  const formatTooltipContent = (tooltip) => {
    if (!tooltip) return 'Loading...';

    const parts = [];
    if (Object.keys(tooltip.detected_attributes || {}).length > 0) {
      parts.push('Detected: ' + Object.entries(tooltip.detected_attributes)
        .map(([k, v]) => `${ATTRIBUTE_LABELS[k] || k}=${v}`).join(', '));
    }
    if (Object.keys(tooltip.variant_attributes || {}).length > 0) {
      parts.push('Variant has: ' + Object.entries(tooltip.variant_attributes)
        .map(([k, v]) => `${ATTRIBUTE_LABELS[k] || k}=${v}`).join(', '));
    }
    if (Object.keys(tooltip.unassigned_attributes || {}).length > 0) {
      parts.push('⚠ Unassigned: ' + Object.entries(tooltip.unassigned_attributes)
        .map(([k, v]) => `${ATTRIBUTE_LABELS[k] || k}=${v}`).join(', '));
    }
    return parts.join('\n') || 'No attributes detected';
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
            const variantCount = countVariants(filteredVariants);

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

                {/* Variants (rendered recursively for hierarchy) */}
                {isExpanded && (
                  <div className="variants-container">
                    {filteredVariants.length === 0 ? (
                      <div className="no-variants">No variants match filters</div>
                    ) : (
                      <VariantTree
                        variants={filteredVariants}
                        baseId={base.id}
                        depth={0}
                        expandedVariants={expandedVariants}
                        toggleVariantExpanded={toggleVariantExpanded}
                        mergeMode={mergeMode}
                        selectedForMerge={selectedForMerge}
                        toggleMergeSelection={toggleMergeSelection}
                        editingVariant={editingVariant}
                        editForm={editForm}
                        setEditForm={setEditForm}
                        startEditing={startEditing}
                        saveVariantEdit={saveVariantEdit}
                        cancelEditing={cancelEditing}
                        openMoveModal={openMoveModal}
                        getVariantBadges={getVariantBadges}
                        loadingVariants={loadingVariants}
                        commonProductsCache={commonProductsCache}
                        editingCP={editingCP}
                        editCPName={editCPName}
                        setEditCPName={setEditCPName}
                        startEditingCP={startEditingCP}
                        saveCPEdit={saveCPEdit}
                        cancelEditingCP={cancelEditingCP}
                        attributeTooltips={attributeTooltips}
                        loadingTooltip={loadingTooltip}
                        fetchAttributeTooltip={fetchAttributeTooltip}
                        formatTooltipContent={formatTooltipContent}
                        formatPrice={formatPrice}
                        attributeValues={attributeValues}
                        openReassignModal={openReassignModal}
                        EDITABLE_ATTRS={EDITABLE_ATTRS}
                        ATTRIBUTE_LABELS={ATTRIBUTE_LABELS}
                      />
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

      {/* Move Variant Modal */}
      {movingVariant && (
        <div className="modal-overlay" onClick={closeMoveModal}>
          <div className="modal-content move-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Move "{movingVariant.display_name}"</h3>
            <p className="move-hint">Select new parent (or root to make it top-level)</p>

            <div className="move-options">
              <label className={`move-option ${moveTargetId === 'root' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="moveTarget"
                  value="root"
                  checked={moveTargetId === 'root'}
                  onChange={() => setMoveTargetId('root')}
                />
                <span className="option-label">📦 Root (top-level variant)</span>
              </label>

              {/* Show all variants from the same base as potential parents */}
              {(() => {
                const base = baseIngredients.find(b => b.id === movingVariant.baseId);
                if (!base?.variants) return null;

                // Flatten the tree to show all variants
                const allVariants = getAllVariantsFlat(base.variants);

                // Helper to check if a variant is a descendant of the moving variant
                const isDescendantOf = (variantId, ancestorId) => {
                  const findInTree = (variants, targetId) => {
                    for (const v of variants) {
                      if (v.id === targetId) return v;
                      if (v.children) {
                        const found = findInTree(v.children, targetId);
                        if (found) return found;
                      }
                    }
                    return null;
                  };
                  const ancestor = findInTree(base.variants, ancestorId);
                  if (!ancestor?.children) return false;
                  const checkDescendants = (children) => {
                    for (const c of children) {
                      if (c.id === variantId) return true;
                      if (c.children && checkDescendants(c.children)) return true;
                    }
                    return false;
                  };
                  return checkDescendants(ancestor.children);
                };

                return allVariants
                  .filter(v => v.id !== movingVariant.id)
                  .filter(v => !isDescendantOf(v.id, movingVariant.id))
                  .map(v => (
                    <label
                      key={v.id}
                      className={`move-option ${moveTargetId === v.id.toString() ? 'selected' : ''}`}
                      style={{ marginLeft: (v.depth || 0) * 16 }}
                    >
                      <input
                        type="radio"
                        name="moveTarget"
                        value={v.id}
                        checked={moveTargetId === v.id.toString()}
                        onChange={() => setMoveTargetId(v.id.toString())}
                      />
                      <span className="option-label">
                        {v.depth > 0 && '└ '}{v.display_name}
                      </span>
                    </label>
                  ));
              })()}
            </div>

            <div className="modal-actions">
              <button onClick={closeMoveModal} className="btn-secondary">Cancel</button>
              <button onClick={executeMove} className="btn-primary">Move</button>
            </div>
          </div>
        </div>
      )}

      {/* Reassign Product Modal */}
      {reassigningProduct && (
        <div className="modal-overlay" onClick={closeReassignModal}>
          <div className="modal-content reassign-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Move Product to Different CP</h3>
            <p className="reassign-product-name">{reassigningProduct.product_name}</p>
            <p className="reassign-hint">Search for the common product to move this SKU to:</p>

            <input
              type="text"
              className="cp-search-input"
              placeholder="Search common products..."
              value={cpSearchQuery}
              onChange={(e) => setCpSearchQuery(e.target.value)}
              autoFocus
            />

            <div className="cp-search-results">
              {searchingCPs ? (
                <div className="searching">Searching...</div>
              ) : cpSearchResults.length === 0 ? (
                <div className="no-results">
                  {cpSearchQuery.length < 2 ? 'Type at least 2 characters to search' : 'No matches found'}
                </div>
              ) : (
                cpSearchResults.map(cp => (
                  <div
                    key={cp.id}
                    className={`cp-result ${selectedNewCP?.id === cp.id ? 'selected' : ''}`}
                    onClick={() => setSelectedNewCP(cp)}
                  >
                    <span className="cp-result-name">{cp.common_name}</span>
                    {cp.variant_name && (
                      <span className="cp-result-variant">→ {cp.variant_name}</span>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="modal-actions">
              <button onClick={closeReassignModal} className="btn-secondary">Cancel</button>
              <button
                onClick={executeReassign}
                className="btn-primary"
                disabled={!selectedNewCP}
              >
                Move to {selectedNewCP?.common_name || '...'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TaxonomyView;
