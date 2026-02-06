import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../contexts/ToastContext';
import { createRecipeFromParse } from '../../services/aiParseService';
import './RecipeImport.css';

export default function ReviewParsedRecipe({ parseResult, outletId, onClose }) {
  const [recipeName, setRecipeName] = useState(parseResult.recipe_name || '');
  const [description, setDescription] = useState(parseResult.description || '');
  const [category, setCategory] = useState(parseResult.category || '');
  const [yieldQuantity, setYieldQuantity] = useState(parseResult.yield_info?.quantity || '');
  const [yieldUnit, setYieldUnit] = useState(parseResult.yield_info?.unit || '');
  const [creating, setCreating] = useState(false);

  const navigate = useNavigate();
  const toast = useToast();

  const handleCreateRecipe = async () => {
    setCreating(true);

    try {
      // Create recipe with all ingredients as text-only (unmapped)
      const ingredients = parseResult.ingredients.map(ing => ({
        ingredient_name: ing.parsed_name,
        quantity: ing.normalized_quantity,
        unit_id: ing.normalized_unit_id,
        notes: ing.prep_note
      }));

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

      console.log('[REVIEW] Recipe created successfully:', response);

      // Close modal and navigate
      onClose();
      toast.success(`Recipe "${recipeName}" created successfully!`);
      navigate('/recipes');

    } catch (err) {
      console.error('Create error:', err);
      toast.error(err.response?.data?.detail || 'Error creating recipe');
      setCreating(false);
    }
  };

  const displayQuantity = (ing) => {
    const qty = `${ing.quantity} ${ing.unit}`;
    if (ing.quantity !== ing.normalized_quantity) {
      return `${qty} (${ing.normalized_quantity} ${ing.normalized_unit})`;
    }
    return qty;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content review-parsed-recipe" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header review-header">
          <div>
            <h2>Review Extracted Recipe</h2>
            <p className="review-header-subtitle">
              Review the extracted data. Fix any critical errors before saving.
            </p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {/* Notice */}
          <div className="review-info-notice">
            <div className="review-info-content">
              <span className="review-info-icon">ℹ️</span>
              <div>
                <p className="review-info-title">Quick Review Only</p>
                <p className="review-info-text">
                  This screen is for catching critical errors. Full editing, product mapping, and cost calculation
                  can be done after saving the recipe.
                </p>
              </div>
            </div>
          </div>

          {/* Recipe Info Form */}
          <div className="review-recipe-form">
            <div>
              <label className="review-form-label">Recipe Name *</label>
              <input
                type="text"
                className="review-form-input"
                value={recipeName}
                onChange={(e) => setRecipeName(e.target.value)}
                placeholder="Enter recipe name"
              />
            </div>

            <div className="yield-inputs">
              <div>
                <label className="review-form-label">Yield Quantity</label>
                <input
                  type="number"
                  step="0.1"
                  className="review-form-input"
                  value={yieldQuantity}
                  onChange={(e) => setYieldQuantity(e.target.value)}
                  placeholder="2"
                />
              </div>
              <div>
                <label className="review-form-label">Yield Unit</label>
                <input
                  type="text"
                  className="review-form-input"
                  value={yieldUnit}
                  onChange={(e) => setYieldUnit(e.target.value)}
                  placeholder="quart"
                />
              </div>
            </div>

            <div>
              <label className="review-form-label">Category</label>
              <input
                type="text"
                className="review-form-input"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g., Sauces, Entrees"
              />
            </div>

            <div>
              <label className="review-form-label">Description</label>
              <textarea
                className="review-form-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Optional description"
              />
            </div>
          </div>

          {/* Ingredients Section - Read-only Display */}
          <div className="ingredients-section">
            <div className="ingredients-header">
              <div className="ingredients-count">
                Ingredients ({parseResult.ingredients.length})
              </div>
              <div className="ingredients-mapping-note">
                Product mapping available after saving
              </div>
            </div>

            <div className="ingredients-list-container">
              {parseResult.ingredients.map((ingredient, idx) => (
                <div key={idx} className="ingredient-display-row">
                  <div className="ingredient-display-info">
                    <div className="ingredient-display-name">
                      {ingredient.parsed_name}
                    </div>
                    {ingredient.prep_note && (
                      <div className="ingredient-display-prep">
                        {ingredient.prep_note}
                      </div>
                    )}
                  </div>
                  <div className="ingredient-display-quantity">
                    {displayQuantity(ingredient)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={creating}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleCreateRecipe}
            disabled={!recipeName || creating}
          >
            {creating ? 'Creating Recipe...' : 'Save Recipe'}
          </button>
        </div>
      </div>
    </div>
  );
}
