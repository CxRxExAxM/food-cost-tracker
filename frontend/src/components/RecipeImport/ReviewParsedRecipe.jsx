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

  // Track user overrides for unmatched ingredients
  // Key: ingredient index, Value: { product_id, product_name } or null (skipped)
  const [userSelections, setUserSelections] = useState({});

  const navigate = useNavigate();
  const toast = useToast();

  // Handle user accepting a suggestion
  const handleAcceptSuggestion = (idx, product) => {
    setUserSelections(prev => ({
      ...prev,
      [idx]: { product_id: product.common_product_id, product_name: product.common_name }
    }));
  };

  // Handle user skipping/dismissing a suggestion
  const handleSkipSuggestion = (idx) => {
    setUserSelections(prev => ({
      ...prev,
      [idx]: null // null means explicitly skipped
    }));
  };

  // Get the effective match for an ingredient (user selection > auto-match > none)
  const getEffectiveMatch = (ingredient, idx) => {
    // Check user selection first
    if (idx in userSelections) {
      return userSelections[idx]; // Could be { product_id, product_name } or null
    }
    // Fall back to auto-match
    if (ingredient.auto_matched_product_id) {
      return {
        product_id: ingredient.auto_matched_product_id,
        product_name: ingredient.auto_matched_product_name
      };
    }
    return undefined; // No match yet, show suggestion if available
  };

  // Count total matched (auto + user accepted)
  const getMatchedCount = () => {
    return parseResult.ingredients.filter((ing, idx) => {
      const match = getEffectiveMatch(ing, idx);
      return match && match.product_id;
    }).length;
  };

  const handleCreateRecipe = async () => {
    setCreating(true);

    try {
      // Create recipe - use user selections > auto-matched > text name
      const ingredients = parseResult.ingredients.map((ing, idx) => {
        const effectiveMatch = getEffectiveMatch(ing, idx);
        const productId = effectiveMatch?.product_id || null;

        return {
          common_product_id: productId,
          ingredient_name: productId ? null : ing.parsed_name,
          quantity: ing.normalized_quantity,
          unit_id: ing.normalized_unit_id,
          notes: ing.prep_note
        };
      });

      await createRecipeFromParse({
        parse_id: parseResult.parse_id,
        name: recipeName,
        outlet_id: outletId,
        yield_quantity: yieldQuantity ? parseFloat(yieldQuantity) : null,
        yield_unit_id: parseResult.yield_info?.unit_id || null,
        description,
        category,
        ingredients
      });

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

          {/* Ingredients Section */}
          <div className="ingredients-section">
            <div className="ingredients-header">
              <div className="ingredients-count">
                Ingredients ({parseResult.ingredients.length})
                <span className="ingredients-matched-count">
                  {' '}• {getMatchedCount()} matched
                </span>
              </div>
              <div className="ingredients-mapping-note">
                Unmatched items can be mapped after saving
              </div>
            </div>

            <div className="ingredients-list-container">
              {parseResult.ingredients.map((ingredient, idx) => {
                const effectiveMatch = getEffectiveMatch(ingredient, idx);
                const isMatched = effectiveMatch && effectiveMatch.product_id;
                const wasSkipped = idx in userSelections && userSelections[idx] === null;
                const topSuggestion = ingredient.suggested_products?.[0];
                const showSuggestion = !isMatched && !wasSkipped && topSuggestion;

                return (
                  <div
                    key={idx}
                    className={`ingredient-display-row ${isMatched ? 'ingredient-matched' : 'ingredient-unmatched'}`}
                  >
                    <div className="ingredient-display-info">
                      <div className="ingredient-display-name">
                        {ingredient.parsed_name}
                        {isMatched && (
                          <span className="ingredient-match-indicator">
                            {' '}→ {effectiveMatch.product_name}
                          </span>
                        )}
                      </div>
                      {ingredient.prep_note && (
                        <div className="ingredient-display-prep">
                          {ingredient.prep_note}
                        </div>
                      )}
                      {/* "Did you mean?" suggestion for unmatched items */}
                      {showSuggestion && (
                        <div className="ingredient-suggestion">
                          <span className="suggestion-label">Did you mean:</span>
                          <span className="suggestion-name">{topSuggestion.common_name}</span>
                          <span className="suggestion-confidence">({Math.round(topSuggestion.confidence * 100)}%)</span>
                          <button
                            type="button"
                            className="suggestion-btn suggestion-yes"
                            onClick={() => handleAcceptSuggestion(idx, topSuggestion)}
                          >
                            Yes
                          </button>
                          <button
                            type="button"
                            className="suggestion-btn suggestion-skip"
                            onClick={() => handleSkipSuggestion(idx)}
                          >
                            Skip
                          </button>
                        </div>
                      )}
                      {wasSkipped && (
                        <div className="ingredient-skipped-note">
                          Will save as text (map later)
                        </div>
                      )}
                    </div>
                    <div className="ingredient-display-quantity">
                      {displayQuantity(ingredient)}
                    </div>
                  </div>
                );
              })}
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
