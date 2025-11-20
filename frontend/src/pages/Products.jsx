import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './Products.css';

const API_URL = 'http://localhost:8000';

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unmappedOnly, setUnmappedOnly] = useState(false);

  useEffect(() => {
    fetchProducts();
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

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : 'N/A';
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
                <th>Status</th>
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
                  <td>
                    {product.common_product_id ? (
                      <span className="status-badge mapped">Mapped</span>
                    ) : (
                      <span className="status-badge unmapped">Unmapped</span>
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
