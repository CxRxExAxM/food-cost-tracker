import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import axios from '../../lib/axios';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function PathBasedProductMapper({ productDescription, onSelect, onCancel }) {
  const [path, setPath] = useState([]);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [creating, setCreating] = useState(false);
  const [createIntent, setCreateIntent] = useState(null); // 'variant' | 'common_product' | null

  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  // On mount: get parser suggestion and pre-navigate the path
  useEffect(() => {
    if (!productDescription) return;
    axios.get(`${API_URL}/taxonomy/suggest-path`, { params: { name: productDescription } })
      .then(res => {
        if (res.data.suggested_path?.length > 0) {
          setPath(res.data.suggested_path);
        }
      })
      .catch(() => {});
  }, [productDescription]);

  // Debounced search whenever path or query changes
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchResults();
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [path, query]);

  // Reset highlight when results change
  useEffect(() => {
    setHighlightedIndex(0);
  }, [results]);

  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (path.length > 0) params.path = path.join(',');
      if (query.trim()) params.query = query.trim();
      const res = await axios.get(`${API_URL}/taxonomy/search-path`, { params });
      setResults(res.data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [path, query]);

  const selectResult = useCallback(async (item) => {
    if (item.type === 'base_ingredient' || item.type === 'variant') {
      setPath(prev => [...prev, item.name]);
      setQuery('');
      inputRef.current?.focus();
    } else if (item.type === 'common_product') {
      onSelect({ id: item.id, common_name: item.name });
    }
  }, [onSelect]);

  const createItem = useCallback(async (type) => {
    const name = query.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      const res = await axios.post(`${API_URL}/taxonomy/create-in-path`, {
        path,
        name,
        type
      });
      if (type === 'variant') {
        setPath(prev => [...prev, name]);
        setQuery('');
        inputRef.current?.focus();
      } else if (type === 'common_product') {
        onSelect({ id: res.data.id, common_name: res.data.common_name });
      } else if (type === 'base_ingredient') {
        setPath([name]);
        setQuery('');
        inputRef.current?.focus();
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create item');
    } finally {
      setCreating(false);
    }
  }, [path, query, creating, onSelect]);

  const goBack = () => {
    setPath(prev => prev.slice(0, -1));
    setQuery('');
    setCreateIntent(null);
  };

  const handleKeyDown = (e) => {
    const allItems = buildAllItems();

    if (e.key === 'Escape') {
      onCancel();
      return;
    }

    if (e.key === 'Backspace' && query === '') {
      e.preventDefault();
      goBack();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex(i => Math.min(i + 1, allItems.length - 1));
      return;
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(i => Math.max(i - 1, 0));
      return;
    }

    if (e.key === 'Enter' && allItems.length > 0) {
      e.preventDefault();
      const item = allItems[highlightedIndex];
      if (item) handleItemAction(item);
      return;
    }

    // Comma or Tab: advance into highlighted variant
    if ((e.key === ',' || e.key === 'Tab') && results.length > 0) {
      const topVariant = results.find(r => r.type === 'variant');
      if (topVariant) {
        e.preventDefault();
        selectResult(topVariant);
      }
    }
  };

  const handleItemAction = (item) => {
    if (item._action === 'create_variant') createItem('variant');
    else if (item._action === 'create_cp') createItem('common_product');
    else if (item._action === 'create_base') createItem('base_ingredient');
    else if (item._action === 'suggest_cp_name') suggestCPName();
    else selectResult(item);
  };

  const suggestCPName = () => {
    setQuery(path.join(', '));
    setCreateIntent('common_product');
    inputRef.current?.focus();
  };

  // Build the full item list for keyboard navigation (results + create options)
  const buildAllItems = () => {
    const items = [...results];
    if (query.trim()) {
      const exactMatch = results.some(r => r.name.toLowerCase() === query.trim().toLowerCase());
      if (!exactMatch || path.length > 0) {
        if (path.length > 0) {
          items.push({ _action: 'create_variant', name: query.trim(), type: '_create' });
          items.push({ _action: 'create_cp', name: query.trim(), type: '_create' });
        } else {
          items.push({ _action: 'create_base', name: query.trim(), type: '_create' });
        }
      }
    }
    // Always offer CP creation at a variant level, even with empty query
    if (path.length > 0 && !query.trim()) {
      items.push({ _action: 'suggest_cp_name', type: '_suggest' });
    }
    return items;
  };

  const allItems = buildAllItems();
  const hasCreateOptions = query.trim() && !results.some(r => r.name.toLowerCase() === query.trim().toLowerCase());

  const getDropdownStyle = () => {
    if (!inputRef.current) return {};
    const r = inputRef.current.getBoundingClientRect();
    return { position: 'fixed', top: r.bottom + 4, left: r.left, width: r.width, zIndex: 9999 };
  };

  const showDropdown = results.length > 0 || hasCreateOptions || (path.length > 0 && !query.trim());

  return (
    <div className="path-mapper">
      <div className="path-mapper-breadcrumb">
        {path.length === 0 && (
          <span className="path-mapper-hint">Type to search or navigate the taxonomy</span>
        )}
        {path.map((step, i) => (
          <span key={i} className="path-mapper-crumb">
            {i > 0 && <span className="path-mapper-sep">›</span>}
            <button
              className="path-mapper-crumb-btn"
              onClick={() => {
                setPath(path.slice(0, i + 1));
                setQuery('');
                inputRef.current?.focus();
              }}
            >
              {step}
            </button>
          </span>
        ))}
        {path.length > 0 && <span className="path-mapper-sep">›</span>}
      </div>

      <div className="path-mapper-input-wrap">
        <input
          ref={inputRef}
          type="text"
          className="mapping-input"
          value={query}
          onChange={e => { setQuery(e.target.value); setCreateIntent(null); }}
          onKeyDown={handleKeyDown}
          placeholder={path.length === 0 ? 'Search base ingredient...' : 'Search or create...'}
          autoFocus
        />

        {showDropdown && createPortal(
          <div className="autocomplete-dropdown" style={getDropdownStyle()}>
            {results.map((item, i) => (
              <div
                key={`${item.type}-${item.id}`}
                className={`autocomplete-item path-mapper-item ${highlightedIndex === i ? 'highlighted' : ''}`}
                onClick={() => selectResult(item)}
                onMouseEnter={() => setHighlightedIndex(i)}
              >
                <span className="path-mapper-item-icon">
                  {item.type === 'base_ingredient' && '⬡'}
                  {item.type === 'variant' && '📁'}
                  {item.type === 'common_product' && '📦'}
                </span>
                <span className="path-mapper-item-name">{item.name}</span>
                <span className="path-mapper-item-meta">
                  {item.type === 'base_ingredient' && item.variant_count > 0 && `${item.variant_count} variants`}
                  {item.type === 'variant' && item.has_children && 'has sub-variants'}
                  {item.type === 'variant' && !item.has_children && item.common_product_count > 0 && `${item.common_product_count} products`}
                  {item.type === 'common_product' && item.category}
                </span>
              </div>
            ))}

            {query.trim() && path.length > 0 && (
              <>
                {hasCreateOptions && results.length > 0 && (
                  <div className="path-mapper-divider" />
                )}
                {createIntent !== 'common_product' && (
                  <div
                    className={`autocomplete-item create-new ${highlightedIndex === results.length ? 'highlighted' : ''}`}
                    onClick={() => createItem('variant')}
                    onMouseEnter={() => setHighlightedIndex(results.length)}
                  >
                    {creating ? 'Creating...' : `+ Create "${query.trim()}" as variant`}
                  </div>
                )}
                {createIntent !== 'variant' && (
                  <div
                    className={`autocomplete-item create-new ${highlightedIndex === (createIntent === 'common_product' ? results.length : results.length + 1) ? 'highlighted' : ''}`}
                    onClick={() => createItem('common_product')}
                    onMouseEnter={() => setHighlightedIndex(createIntent === 'common_product' ? results.length : results.length + 1)}
                  >
                    {creating ? 'Creating...' : `+ Create "${query.trim()}" as Common Product`}
                  </div>
                )}
              </>
            )}

            {query.trim() && path.length === 0 && (
              <div
                className={`autocomplete-item create-new ${highlightedIndex === results.length ? 'highlighted' : ''}`}
                onClick={() => createItem('base_ingredient')}
                onMouseEnter={() => setHighlightedIndex(results.length)}
              >
                {creating ? 'Creating...' : `+ Create "${query.trim()}" as base ingredient`}
              </div>
            )}

            {path.length > 0 && !query.trim() && (
              <>
                {results.length > 0 && <div className="path-mapper-divider" />}
                <div
                  className={`autocomplete-item create-new ${highlightedIndex === results.length ? 'highlighted' : ''}`}
                  onClick={suggestCPName}
                  onMouseEnter={() => setHighlightedIndex(results.length)}
                >
                  📦 Create a Common Product here
                </div>
              </>
            )}
          </div>,
          document.body
        )}

        {loading && results.length === 0 && createPortal(
          <div className="autocomplete-dropdown" style={getDropdownStyle()}>
            <div className="autocomplete-item" style={{ color: 'var(--text-tertiary)' }}>Searching...</div>
          </div>,
          document.body
        )}
      </div>

      <div className="mapping-actions">
        <button onClick={onCancel} className="btn-cancel">Cancel</button>
        {path.length > 0 && (
          <button onClick={goBack} className="btn-cancel">← Back</button>
        )}
      </div>
    </div>
  );
}
