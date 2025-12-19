import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
      alert(`Recipe "${recipeName}" created successfully!`);
      navigate('/recipes');

    } catch (err) {
      console.error('Create error:', err);
      alert(err.response?.data?.detail || 'Error creating recipe');
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
            <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
              Review the extracted data. Fix any critical errors before saving.
            </p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {/* Notice */}
          <div style={{
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1.5rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'start', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.25rem' }}>ℹ️</span>
              <div>
                <p style={{ fontSize: '0.875rem', color: '#1e40af', fontWeight: 500, marginBottom: '0.25rem' }}>
                  Quick Review Only
                </p>
                <p style={{ fontSize: '0.875rem', color: '#1e3a8a', lineHeight: '1.4' }}>
                  This screen is for catching critical errors. Full editing, product mapping, and cost calculation
                  can be done after saving the recipe.
                </p>
              </div>
            </div>
          </div>

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

          {/* Ingredients Section - Read-only Display */}
          <div className="ingredients-section">
            <div className="ingredients-header">
              <div className="ingredients-count">
                Ingredients ({parseResult.ingredients.length})
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Product mapping available after saving
              </div>
            </div>

            <div style={{
              background: '#f9fafb',
              borderRadius: '6px',
              border: '1px solid #e5e7eb',
              padding: '1rem'
            }}>
              {parseResult.ingredients.map((ingredient, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem 0',
                    borderBottom: idx < parseResult.ingredients.length - 1 ? '1px solid #e5e7eb' : 'none',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start'
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, color: '#1f2937' }}>
                      {ingredient.parsed_name}
                    </div>
                    {ingredient.prep_note && (
                      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.125rem' }}>
                        {ingredient.prep_note}
                      </div>
                    )}
                  </div>
                  <div style={{
                    fontSize: '0.875rem',
                    color: '#6b7280',
                    textAlign: 'right',
                    marginLeft: '1rem'
                  }}>
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
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            {creating ? 'Creating Recipe...' : (
              <>
                <span>Save Recipe</span>
                <span style={{
                  padding: '0.125rem 0.5rem',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '4px',
                  fontSize: '0.75rem'
                }}>
                  Uses 1 ⭐
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
