import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import IngredientMatchRow from './IngredientMatchRow';
import { createRecipeFromParse } from '../../services/aiParseService';
import './RecipeImport.css';

export default function ReviewParsedRecipe({ parseResult, outletId, onClose }) {
  const [recipeName, setRecipeName] = useState(parseResult.recipe_name || '');
  const [description, setDescription] = useState(parseResult.description || '');
  const [category, setCategory] = useState(parseResult.category || '');
  const [yieldQuantity, setYieldQuantity] = useState(parseResult.yield_info?.quantity || '');
  const [yieldUnit, setYieldUnit] = useState(parseResult.yield_info?.unit || '');
  const [ingredientSelections, setIngredientSelections] = useState({});
  const [creating, setCreating] = useState(false);

  const navigate = useNavigate();

  const handleProductSelected = (ingredientName, ingredientData) => {
    setIngredientSelections(prev => ({
      ...prev,
      [ingredientName]: ingredientData
    }));
  };

  const handleCreateRecipe = async () => {
    // Validate all ingredients have products selected
    const unselected = parseResult.ingredients.filter(
      ing => !ingredientSelections[ing.parsed_name]
    );

    if (unselected.length > 0) {
      alert(`Please select products for all ingredients. ${unselected.length} ingredient(s) still need selection.`);
      return;
    }

    setCreating(true);

    try {
      // Build ingredients array
      const ingredients = Object.values(ingredientSelections);

      // Create recipe
      const response = await createRecipeFromParse({
        parse_id: parseResult.parse_id,
        name: recipeName,
        outlet_id: outletId,
        yield_quantity: yieldQuantity ? parseFloat(yieldQuantity) : null,
        yield_unit_id: parseResult.yield_info?.unit_id || null,
        description,
        category,
        ingredients
      });

      // Navigate to recipe editor
      navigate(`/recipes/${response.recipe_id}/edit`);

    } catch (err) {
      console.error('Create error:', err);
      alert(err.response?.data?.detail || 'Error creating recipe');
      setCreating(false);
    }
  };

  const selectedCount = Object.keys(ingredientSelections).length;
  const totalCount = parseResult.ingredients.length;
  const allSelected = selectedCount === totalCount;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content review-parsed-recipe" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header review-header">
          <div>
            <h2>Review Parsed Recipe</h2>
            <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
              Review and confirm ingredient-to-product matches before creating recipe
            </p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {/* Recipe Info Form */}
          <div className="review-recipe-form">
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                Recipe Name *
              </label>
              <input
                type="text"
                value={recipeName}
                onChange={(e) => setRecipeName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px'
                }}
                placeholder="Enter recipe name"
              />
            </div>

            <div className="yield-inputs">
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                  Yield Quantity
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={yieldQuantity}
                  onChange={(e) => setYieldQuantity(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px'
                  }}
                  placeholder="2"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                  Yield Unit
                </label>
                <input
                  type="text"
                  value={yieldUnit}
                  onChange={(e) => setYieldUnit(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px'
                  }}
                  placeholder="quart"
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                Category
              </label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px'
                }}
                placeholder="e.g., Sauces, Entrees"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  resize: 'vertical'
                }}
                placeholder="Optional description"
              />
            </div>
          </div>

          {/* Ingredients Section */}
          <div className="ingredients-section">
            <div className="ingredients-header">
              <div className="ingredients-count">
                Ingredients ({totalCount})
              </div>
              {!allSelected && (
                <div className="review-status">
                  <span>⚠️</span>
                  <span>{totalCount - selectedCount} ingredient(s) need product selection</span>
                </div>
              )}
              {allSelected && (
                <div className="review-status" style={{ color: '#10b981' }}>
                  <span>✓</span>
                  <span>All ingredients matched</span>
                </div>
              )}
            </div>

            {parseResult.ingredients.map((ingredient, idx) => (
              <IngredientMatchRow
                key={idx}
                ingredient={ingredient}
                onProductSelected={handleProductSelected}
              />
            ))}
          </div>

          {/* Review Summary */}
          {!allSelected && (
            <div className="review-summary">
              <div className="review-summary-text">
                <span>⚠️</span>
                <span>
                  Please select products for all {totalCount - selectedCount} remaining ingredient(s) before creating recipe
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={creating}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleCreateRecipe}
            disabled={!allSelected || !recipeName || creating}
          >
            {creating ? 'Creating Recipe...' : 'Save as Draft →'}
          </button>
        </div>
      </div>
    </div>
  );
}
