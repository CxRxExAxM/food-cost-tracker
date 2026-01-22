import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Package, ChefHat, X } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function LinkPrepItemModal({ prepItem, onClose, onLinked }) {
  const [linkType, setLinkType] = useState(prepItem.product_id ? 'product' : prepItem.recipe_id ? 'recipe' : 'product');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const currentLink = prepItem.product_id
    ? { type: 'product', id: prepItem.product_id, name: prepItem.product_name }
    : prepItem.recipe_id
    ? { type: 'recipe', id: prepItem.recipe_id, name: prepItem.recipe_name }
    : null;

  useEffect(() => {
    if (searchTerm.length >= 2) {
      const timer = setTimeout(() => {
        performSearch();
      }, 300);
      return () => clearTimeout(timer);
    } else {
      setSearchResults([]);
    }
  }, [searchTerm, linkType]);

  const performSearch = async () => {
    setSearching(true);
    try {
      if (linkType === 'product') {
        const response = await axios.get(`${API_URL}/api/products`, {
          params: { search: searchTerm, limit: 20 },
          withCredentials: true
        });
        setSearchResults(response.data.products || []);
      } else {
        const response = await axios.get(`${API_URL}/api/recipes`, {
          params: { search: searchTerm, limit: 20 },
          withCredentials: true
        });
        setSearchResults(response.data.recipes || []);
      }
    } catch (err) {
      console.error('Error searching:', err);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleLink = async (item) => {
    setSaving(true);
    setError(null);

    try {
      const payload = linkType === 'product'
        ? { product_id: item.id, recipe_id: null }
        : { recipe_id: item.id, product_id: null };

      await axios.put(`${API_URL}/api/banquet-menus/prep/${prepItem.id}`, payload, {
        withCredentials: true
      });

      onLinked();
    } catch (err) {
      console.error('Error linking prep item:', err);
      setError(err.response?.data?.detail || 'Failed to link prep item');
      setSaving(false);
    }
  };

  const handleUnlink = async () => {
    setSaving(true);
    setError(null);

    try {
      await axios.put(`${API_URL}/api/banquet-menus/prep/${prepItem.id}`, {
        product_id: null,
        recipe_id: null
      }, {
        withCredentials: true
      });

      onLinked();
    } catch (err) {
      console.error('Error unlinking prep item:', err);
      setError(err.response?.data?.detail || 'Failed to unlink prep item');
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Link "{prepItem.name}"</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {error && <div className="error-message">{error}</div>}

          {/* Current Link Display */}
          {currentLink && (
            <div style={{
              marginBottom: 'var(--space-5)',
              padding: 'var(--space-4)',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', textTransform: 'uppercase' }}>
                  Currently linked to {currentLink.type}:
                </span>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 'var(--space-1)' }}>
                  {currentLink.name}
                </div>
              </div>
              <button
                onClick={handleUnlink}
                disabled={saving}
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  background: 'var(--color-red-dim)',
                  color: 'var(--color-red-bright)',
                  border: '1px solid var(--color-red)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600
                }}
              >
                <X size={12} style={{ marginRight: '4px' }} />
                Unlink
              </button>
            </div>
          )}

          {/* Link Type Tabs */}
          <div style={{
            display: 'flex',
            gap: 'var(--space-2)',
            marginBottom: 'var(--space-4)'
          }}>
            <button
              onClick={() => { setLinkType('product'); setSearchTerm(''); setSearchResults([]); }}
              style={{
                flex: 1,
                padding: 'var(--space-3)',
                background: linkType === 'product' ? 'var(--color-yellow-dim)' : 'var(--bg-tertiary)',
                border: `1px solid ${linkType === 'product' ? 'var(--color-yellow)' : 'var(--border-default)'}`,
                borderRadius: 'var(--radius-md)',
                color: linkType === 'product' ? 'var(--color-yellow-bright)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
                fontWeight: 500
              }}
            >
              <Package size={16} />
              Products
            </button>
            <button
              onClick={() => { setLinkType('recipe'); setSearchTerm(''); setSearchResults([]); }}
              style={{
                flex: 1,
                padding: 'var(--space-3)',
                background: linkType === 'recipe' ? 'rgba(59, 130, 246, 0.2)' : 'var(--bg-tertiary)',
                border: `1px solid ${linkType === 'recipe' ? 'var(--color-blue)' : 'var(--border-default)'}`,
                borderRadius: 'var(--radius-md)',
                color: linkType === 'recipe' ? 'var(--color-blue)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
                fontWeight: 500
              }}
            >
              <ChefHat size={16} />
              Recipes
            </button>
          </div>

          {/* Search Input */}
          <div style={{ position: 'relative', marginBottom: 'var(--space-4)' }}>
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: 'var(--space-3)',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-tertiary)'
              }}
            />
            <input
              type="text"
              className="form-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={`Search ${linkType === 'product' ? 'products' : 'recipes'}...`}
              style={{ paddingLeft: 'var(--space-10)' }}
              autoFocus
            />
          </div>

          {/* Search Results */}
          <div style={{
            maxHeight: '300px',
            overflowY: 'auto',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)'
          }}>
            {searching && (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                Searching...
              </div>
            )}

            {!searching && searchTerm.length >= 2 && searchResults.length === 0 && (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                No {linkType === 'product' ? 'products' : 'recipes'} found
              </div>
            )}

            {!searching && searchTerm.length < 2 && (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                Type at least 2 characters to search
              </div>
            )}

            {!searching && searchResults.map((item) => (
              <div
                key={item.id}
                onClick={() => handleLink(item)}
                style={{
                  padding: 'var(--space-3) var(--space-4)',
                  borderBottom: '1px solid var(--border-subtle)',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  transition: 'background var(--transition-fast)',
                  opacity: saving ? 0.5 : 1
                }}
                onMouseEnter={(e) => { if (!saving) e.currentTarget.style.background = 'var(--bg-tertiary)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                  {item.name}
                </div>
                {linkType === 'product' && item.brand && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-yellow)', marginTop: 'var(--space-1)' }}>
                    {item.brand}
                  </div>
                )}
                {linkType === 'recipe' && item.cost_per_serving && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                    Cost per serving: ${parseFloat(item.cost_per_serving).toFixed(2)}
                  </div>
                )}
                {linkType === 'product' && item.unit_price && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                    Unit price: ${parseFloat(item.unit_price).toFixed(4)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default LinkPrepItemModal;
