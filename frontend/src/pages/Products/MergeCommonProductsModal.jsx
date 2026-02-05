import { useState } from 'react';
import axios from '../../lib/axios';

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

function MergeCommonProductsModal({ selectedProducts, onClose, onMergeComplete }) {
  const [targetId, setTargetId] = useState(null);
  const [merging, setMerging] = useState(false);
  const [error, setError] = useState(null);

  // Calculate merged allergens (OR logic)
  const getMergedAllergens = () => {
    const merged = [];
    for (const allergen of ALLERGENS) {
      if (selectedProducts.some(p => p[allergen.key])) {
        merged.push(allergen);
      }
    }
    return merged;
  };

  // Calculate total linked products
  const getTotalLinkedProducts = () => {
    return selectedProducts.reduce((sum, p) => sum + (p.linked_products_count || 0), 0);
  };

  const handleMerge = async () => {
    if (!targetId) {
      setError('Please select a target product to keep');
      return;
    }

    setMerging(true);
    setError(null);

    try {
      const sourceIds = selectedProducts
        .filter(p => p.id !== targetId)
        .map(p => p.id);

      await axios.post(`${API_URL}/common-products/merge`, {
        source_ids: sourceIds,
        target_id: targetId
      });

      onMergeComplete();
    } catch (err) {
      console.error('Error merging products:', err);
      setError(err.response?.data?.detail || 'Failed to merge products');
    } finally {
      setMerging(false);
    }
  };

  const mergedAllergens = getMergedAllergens();
  const totalLinked = getTotalLinkedProducts();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content merge-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Merge Common Products</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <p className="merge-instruction">
            Select which product to keep (others will be merged into it):
          </p>

          <div className="merge-products-list">
            {selectedProducts.map(product => (
              <label
                key={product.id}
                className={`merge-product-option ${targetId === product.id ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="targetProduct"
                  value={product.id}
                  checked={targetId === product.id}
                  onChange={() => setTargetId(product.id)}
                />
                <div className="merge-product-info">
                  <span className="merge-product-name">{product.common_name}</span>
                  <span className="merge-product-linked">
                    ({product.linked_products_count || 0} linked)
                  </span>
                </div>
                {product.category && (
                  <span className="merge-product-category">{product.category}</span>
                )}
              </label>
            ))}
          </div>

          <div className="merge-preview">
            <h3>Preview</h3>
            <div className="merge-preview-content">
              <div className="preview-item">
                <span className="preview-label">Products to remap:</span>
                <span className="preview-value">{totalLinked}</span>
              </div>
              <div className="preview-item">
                <span className="preview-label">Merged allergens:</span>
                <div className="preview-allergens">
                  {mergedAllergens.length > 0 ? (
                    mergedAllergens.map(a => (
                      <span
                        key={a.key}
                        className={`allergen-chip active ${a.dietary ? 'dietary' : ''}`}
                        title={a.label}
                      >
                        {a.icon}
                      </span>
                    ))
                  ) : (
                    <span className="no-allergens">None</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="merge-error">
              {error}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn-cancel"
            onClick={onClose}
            disabled={merging}
          >
            Cancel
          </button>
          <button
            className="btn-merge-confirm"
            onClick={handleMerge}
            disabled={!targetId || merging}
          >
            {merging ? 'Merging...' : `Merge ${selectedProducts.length} Products`}
          </button>
        </div>
      </div>
    </div>
  );
}

export default MergeCommonProductsModal;
