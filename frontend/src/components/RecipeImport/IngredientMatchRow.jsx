import { useState } from 'react';
import { quickCreateProduct, searchProducts } from '../../services/aiParseService';
import { useAuth } from '../../context/AuthContext';

export default function IngredientMatchRow({ ingredient, onProductSelected }) {
  const [showOptions, setShowOptions] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(
    ingredient.suggested_products.length > 0 && ingredient.suggested_products[0].exact_match
      ? ingredient.suggested_products[0]
      : null
  );
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [createForm, setCreateForm] = useState({
    common_name: ingredient.parsed_name,
    category: '',
    subcategory: ''
  });
  const [creating, setCreating] = useState(false);

  const { user } = useAuth();

  // Auto-select exact match on mount
  useState(() => {
    if (selectedProduct) {
      onProductSelected(ingredient.parsed_name, {
        common_product_id: selectedProduct.common_product_id,
        quantity: ingredient.normalized_quantity,
        unit_id: ingredient.normalized_unit_id,
        notes: ingredient.prep_note
      });
    }
  }, []);

  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setShowOptions(false);
    setShowCreateForm(false);

    // Notify parent
    onProductSelected(ingredient.parsed_name, {
      common_product_id: product.common_product_id,
      quantity: ingredient.normalized_quantity,
      unit_id: ingredient.normalized_unit_id,
      notes: ingredient.prep_note
    });
  };

  const handleSearch = async (term) => {
    setSearchTerm(term);

    if (term.length < 2) {
      setSearchResults([]);
      return;
    }

    try {
      const results = await searchProducts(term);
      setSearchResults(results);
    } catch (err) {
      console.error('Search error:', err);
    }
  };

  const handleQuickCreate = async () => {
    setCreating(true);

    try {
      const newProduct = await quickCreateProduct({
        ...createForm,
        organization_id: user.organization_id
      });

      // Select the newly created product
      handleSelectProduct({
        common_product_id: newProduct.common_product_id,
        common_name: newProduct.common_name,
        category: newProduct.category,
        confidence: 1.0,
        exact_match: true
      });

      setShowCreateForm(false);
    } catch (err) {
      console.error('Create error:', err);
      alert(err.response?.data?.detail || 'Error creating product');
    } finally {
      setCreating(false);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.7) return 'medium';
    return 'low';
  };

  const displayQuantity = `${ingredient.quantity} ${ingredient.unit}${ingredient.quantity !== ingredient.normalized_quantity ? ` (${ingredient.normalized_quantity} ${ingredient.normalized_unit})` : ''}`;

  return (
    <div className={`ingredient-row ${ingredient.needs_review ? 'needs-review' : 'has-match'}`}>
      <div className="ingredient-header">
        <div>
          <div className="ingredient-name">{ingredient.parsed_name}</div>
          <div className="ingredient-quantity">
            {displayQuantity}
            {ingredient.prep_note && <span> - {ingredient.prep_note}</span>}
          </div>
        </div>
        <div className={`ingredient-status-badge ${selectedProduct ? 'matched' : 'needs-review'}`}>
          {selectedProduct ? '✓ Matched' : '⚠️ Needs Review'}
        </div>
      </div>

      <div className="product-selector">
        <div
          className={`product-dropdown ${selectedProduct ? 'has-selection' : ''}`}
          onClick={() => setShowOptions(!showOptions)}
        >
          {selectedProduct ? (
            <span>
              {selectedProduct.common_name}
              {selectedProduct.category && ` (${selectedProduct.category})`}
            </span>
          ) : (
            <span style={{ color: '#9ca3af' }}>Select product...</span>
          )}
        </div>

        {showOptions && (
          <div className="product-options">
            {/* Top 3 suggestions */}
            {ingredient.suggested_products.map((product, idx) => (
              <div
                key={idx}
                className={`product-option ${product.exact_match ? 'exact-match' : ''}`}
                onClick={() => handleSelectProduct(product)}
              >
                <div className="product-option-name">
                  {product.exact_match && '✓ '}{product.common_name}
                </div>
                <div className="product-option-meta">
                  <span>{product.category || 'No category'}</span>
                  <span className={`confidence-score ${getConfidenceColor(product.confidence)}`}>
                    {(product.confidence * 100).toFixed(0)}% match
                  </span>
                </div>
              </div>
            ))}

            {/* Search all products */}
            {ingredient.suggested_products.length === 0 && (
              <div className="search-section" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  placeholder="Search all products..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px'
                  }}
                />
                {searchResults.map((product) => (
                  <div
                    key={product.id}
                    className="product-option"
                    onClick={() => handleSelectProduct({
                      common_product_id: product.id,
                      common_name: product.common_name,
                      category: product.category,
                      confidence: 1.0,
                      exact_match: false
                    })}
                  >
                    <div className="product-option-name">{product.common_name}</div>
                    <div className="product-option-meta">
                      <span>{product.category || 'No category'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Create new product option */}
            <div
              className="product-option"
              onClick={(e) => {
                e.stopPropagation();
                setShowCreateForm(true);
                setShowOptions(false);
              }}
              style={{ borderTop: '2px solid #e5e7eb', background: '#f9fafb' }}
            >
              <div className="product-option-name" style={{ color: '#3b82f6' }}>
                + Create New Product
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Create Form */}
      {showCreateForm && (
        <div className="quick-create-form" onClick={(e) => e.stopPropagation()}>
          <h4>Create "{ingredient.parsed_name}"</h4>

          <div className="form-group">
            <label>Product Name *</label>
            <input
              type="text"
              value={createForm.common_name}
              onChange={(e) => setCreateForm({ ...createForm, common_name: e.target.value })}
              placeholder="e.g., Cucumber"
            />
          </div>

          <div className="form-group">
            <label>Category *</label>
            <select
              value={createForm.category}
              onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })}
            >
              <option value="">Select category...</option>
              <option value="Produce">Produce</option>
              <option value="Dairy">Dairy</option>
              <option value="Meat">Meat</option>
              <option value="Seafood">Seafood</option>
              <option value="Pantry">Pantry</option>
              <option value="Bakery">Bakery</option>
              <option value="Beverages">Beverages</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label>Subcategory</label>
            <input
              type="text"
              value={createForm.subcategory}
              onChange={(e) => setCreateForm({ ...createForm, subcategory: e.target.value })}
              placeholder="Optional"
            />
          </div>

          <div className="quick-create-actions">
            <button
              className="cancel-btn"
              onClick={() => setShowCreateForm(false)}
              disabled={creating}
            >
              Cancel
            </button>
            <button
              className="create-btn"
              onClick={handleQuickCreate}
              disabled={!createForm.common_name || !createForm.category || creating}
            >
              {creating ? 'Creating...' : 'Create & Select'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
