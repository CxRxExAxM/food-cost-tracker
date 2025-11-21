import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './Products.css';

const API_URL = 'http://localhost:8000';

function Products() {
  const [products, setProducts] = useState([]);
  const [commonProducts, setCommonProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unmappedOnly, setUnmappedOnly] = useState(false);
  const [editingProductId, setEditingProductId] = useState(null);
  const [mappingInput, setMappingInput] = useState('');
  const [filteredCommonProducts, setFilteredCommonProducts] = useState([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [editingCommonProductId, setEditingCommonProductId] = useState(null);
  const [commonProductEditInput, setCommonProductEditInput] = useState('');

  useEffect(() => {
    fetchProducts();
    fetchCommonProducts();
  }, [search, unmappedOnly]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const params = {
        limit: 100,
        ...(search && { search }),
        ...(unmappedOnly && { unmapped_only: true })
      };
      const response = await axios.get(`${API_URL}/products`, { params });
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCommonProducts = async () => {
    try {
      const response = await axios.get(`${API_URL}/common-products`, { params: { limit: 1000 } });
      setCommonProducts(response.data);
    } catch (error) {
      console.error('Error fetching common products:', error);
    }
  };

  const handleMappingInputChange = (value) => {
    setMappingInput(value);
    if (value) {
      const filtered = commonProducts.filter(cp =>
        cp.common_name.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredCommonProducts(filtered);
      setShowAutocomplete(true);
    } else {
      setShowAutocomplete(false);
    }
  };

  const handleSelectCommonProduct = async (productId, commonProduct) => {
    try {
      await axios.patch(`${API_URL}/products/${productId}`, {
        common_product_id: commonProduct.id
      });

      // Update the local state
      setProducts(products.map(p =>
        p.id === productId
          ? { ...p, common_product_id: commonProduct.id, common_product_name: commonProduct.common_name }
          : p
      ));

      setEditingProductId(null);
      setMappingInput('');
      setShowAutocomplete(false);
    } catch (error) {
      console.error('Error mapping product:', error);
      alert('Failed to map product');
    }
  };

  const handleCreateAndMapCommonProduct = async (productId) => {
    if (!mappingInput.trim()) return;

    try {
      // Create new common product
      const createResponse = await axios.post(`${API_URL}/common-products`, {
        common_name: mappingInput.trim()
      });

      const newCommonProduct = createResponse.data;

      // Map to the product
      await axios.patch(`${API_URL}/products/${productId}`, {
        common_product_id: newCommonProduct.id
      });

      // Update local state
      setProducts(products.map(p =>
        p.id === productId
          ? { ...p, common_product_id: newCommonProduct.id, common_product_name: newCommonProduct.common_name }
          : p
      ));

      setCommonProducts([...commonProducts, newCommonProduct]);
      setEditingProductId(null);
      setMappingInput('');
      setShowAutocomplete(false);
    } catch (error) {
      console.error('Error creating common product:', error);
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert('Failed to create common product');
      }
    }
  };

  const handleUnmap = async (productId) => {
    try {
      await axios.patch(`${API_URL}/products/${productId}/unmap`);

      setProducts(products.map(p =>
        p.id === productId
          ? { ...p, common_product_id: null, common_product_name: null }
          : p
      ));
    } catch (error) {
      console.error('Error unmapping product:', error);
      alert('Failed to unmap product');
    }
  };

  const startEditing = (product) => {
    setEditingProductId(product.id);
    setMappingInput('');
    setShowAutocomplete(false);
  };

  const cancelEditing = () => {
    setEditingProductId(null);
    setMappingInput('');
    setShowAutocomplete(false);
  };

  const startEditingCommonProduct = (product) => {
    setEditingCommonProductId(product.common_product_id);
    setCommonProductEditInput(product.common_product_name);
  };

  const cancelEditingCommonProduct = () => {
    setEditingCommonProductId(null);
    setCommonProductEditInput('');
  };

  const handleUpdateCommonProduct = async (commonProductId) => {
    if (!commonProductEditInput.trim()) {
      cancelEditingCommonProduct();
      return;
    }

    try {
      await axios.patch(`${API_URL}/common-products/${commonProductId}`, {
        common_name: commonProductEditInput.trim()
      });

      // Update all products with this common_product_id
      setProducts(products.map(p =>
        p.common_product_id === commonProductId
          ? { ...p, common_product_name: commonProductEditInput.trim() }
          : p
      ));

      // Update commonProducts state
      setCommonProducts(commonProducts.map(cp =>
        cp.id === commonProductId
          ? { ...cp, common_name: commonProductEditInput.trim() }
          : cp
      ));

      cancelEditingCommonProduct();
    } catch (error) {
      console.error('Error updating common product:', error);
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert('Failed to update common product');
      }
    }
  };

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : 'N/A';
  };

  const getCommonProductName = (product) => {
    if (!product.common_product_id) return null;
    // Use the common_product_name from the API response
    return product.common_product_name || 'Unknown';
  };

  return (
    <div className="container">
      <Link to="/" className="back-link">← Back to Home</Link>

      <div className="page-header">
        <h1>Products</h1>
        <p>View and manage distributor products</p>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={unmappedOnly}
            onChange={(e) => setUnmappedOnly(e.target.checked)}
          />
          Show unmapped only
        </label>

        <div className="results-count">
          {!loading && `${products.length} products`}
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="empty-state">No products found</div>
      ) : (
        <div className="table-container">
          <table className="products-table">
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Brand</th>
                <th>Distributor</th>
                <th>Pack</th>
                <th>Size</th>
                <th>Unit</th>
                <th className="text-right">Case Price</th>
                <th className="text-right">Unit Price</th>
                <th>Common Product</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td className="product-name">{product.name}</td>
                  <td className="brand-cell">{product.brand}</td>
                  <td className="distributor-cell">{product.distributor_name}</td>
                  <td className="text-center">{product.pack}</td>
                  <td className="text-center">{product.size}</td>
                  <td className="text-center">{product.unit_abbreviation || '-'}</td>
                  <td className="text-right price-cell">{formatPrice(product.case_price)}</td>
                  <td className="text-right price-cell">{formatPrice(product.unit_price)}</td>
                  <td className="mapping-cell">
                    {editingProductId === product.id ? (
                      <div className="mapping-editor">
                        <input
                          type="text"
                          value={mappingInput}
                          onChange={(e) => handleMappingInputChange(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && mappingInput.trim()) {
                              handleCreateAndMapCommonProduct(product.id);
                            } else if (e.key === 'Escape') {
                              cancelEditing();
                            }
                          }}
                          placeholder="Type to search or create..."
                          className="mapping-input"
                          autoFocus
                        />

                        {showAutocomplete && filteredCommonProducts.length > 0 && (
                          <div className="autocomplete-dropdown">
                            {filteredCommonProducts.map((cp) => (
                              <div
                                key={cp.id}
                                className="autocomplete-item"
                                onClick={() => handleSelectCommonProduct(product.id, cp)}
                              >
                                {cp.common_name}
                                {cp.category && <span className="category-tag">{cp.category}</span>}
                              </div>
                            ))}
                          </div>
                        )}

                        {mappingInput && filteredCommonProducts.length === 0 && (
                          <div className="autocomplete-dropdown">
                            <div
                              className="autocomplete-item create-new"
                              onClick={() => handleCreateAndMapCommonProduct(product.id)}
                            >
                              + Create "{mappingInput}"
                            </div>
                          </div>
                        )}

                        <div className="mapping-actions">
                          <button onClick={cancelEditing} className="btn-cancel">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <div className="mapping-display">
                        {product.common_product_id ? (
                          <>
                            {editingCommonProductId === product.common_product_id ? (
                              <div className="common-product-edit">
                                <input
                                  type="text"
                                  value={commonProductEditInput}
                                  onChange={(e) => setCommonProductEditInput(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      handleUpdateCommonProduct(product.common_product_id);
                                    } else if (e.key === 'Escape') {
                                      cancelEditingCommonProduct();
                                    }
                                  }}
                                  onBlur={() => handleUpdateCommonProduct(product.common_product_id)}
                                  className="common-product-edit-input"
                                  autoFocus
                                />
                              </div>
                            ) : (
                              <>
                                <span
                                  className="common-product-badge clickable"
                                  onClick={() => startEditingCommonProduct(product)}
                                  title="Click to edit (affects all products with this mapping)"
                                >
                                  {getCommonProductName(product)}
                                </span>
                                <button
                                  onClick={() => handleUnmap(product.id)}
                                  className="btn-unmap"
                                  title="Unmap this product"
                                >
                                  ×
                                </button>
                              </>
                            )}
                          </>
                        ) : (
                          <button
                            onClick={() => startEditing(product)}
                            className="btn-map"
                          >
                            + Map
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Products;
