import { useState, useEffect } from 'react';
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

  // Expansion state
  const [expandedBases, setExpandedBases] = useState(new Set());

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

  const expandAll = () => {
    setExpandedBases(new Set(baseIngredients.map(b => b.id)));
  };

  const collapseAll = () => {
    setExpandedBases(new Set());
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
        </div>
      </div>

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
                </div>

                {/* Variants */}
                {isExpanded && (
                  <div className="variants-container">
                    {filteredVariants.length === 0 ? (
                      <div className="no-variants">No variants match filters</div>
                    ) : (
                      filteredVariants.map(variant => (
                        <div key={variant.id} className="variant-row">
                          <span className="variant-indent">└─</span>
                          <span className="variant-display-name">
                            {variant.display_name}
                          </span>
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
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default TaxonomyView;
