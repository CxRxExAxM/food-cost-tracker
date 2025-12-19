import { useState, useEffect } from 'react';
import axios from '../lib/axios';
import './CommonProductPanel.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

export default function CommonProductPanel({ commonProductId, onClose }) {
  const [data, setData] = useState(null);
  const [selectedOutlet, setSelectedOutlet] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMappedProducts();
  }, [commonProductId]);

  const fetchMappedProducts = async () => {
    try {
      const response = await axios.get(`${API_URL}/common-products/${commonProductId}/mapped-products`);
      setData(response.data);
    } catch (error) {
      console.error('Error fetching mapped products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUnmap = async (productId) => {
    if (!confirm('Unmap this product? This will remove the connection to the common product.')) return;
    try {
      await axios.patch(`${API_URL}/products/${productId}/unmap`);
      fetchMappedProducts(); // Refresh
    } catch (error) {
      console.error('Error unmapping product:', error);
      alert('Failed to unmap product');
    }
  };

  if (loading) {
    return (
      <div className="panel-overlay">
        <div className="common-product-panel loading">
          <div className="loading-message">Loading...</div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const outlets = Object.keys(data.products_by_outlet);
  const filteredProducts = selectedOutlet === 'all'
    ? data.products_by_outlet
    : { [selectedOutlet]: data.products_by_outlet[selectedOutlet] };

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="common-product-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="panel-header">
          <h2>Products mapped to: {data.common_product.common_name}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* Outlet Filter Tabs */}
        {outlets.length > 1 && (
          <div className="outlet-tabs">
            <button
              className={selectedOutlet === 'all' ? 'active' : ''}
              onClick={() => setSelectedOutlet('all')}
            >
              All ({data.total_count})
            </button>
            {outlets.map(outlet => (
              <button
                key={outlet}
                className={selectedOutlet === outlet ? 'active' : ''}
                onClick={() => setSelectedOutlet(outlet)}
              >
                {outlet} ({data.products_by_outlet[outlet].length})
              </button>
            ))}
          </div>
        )}

        {/* Product Cards */}
        <div className="panel-body">
          {data.total_count === 0 ? (
            <div className="empty-state">
              <p>No products mapped to this common product yet.</p>
              <p className="empty-hint">Map products from the Products page to see them here.</p>
            </div>
          ) : (
            Object.entries(filteredProducts).map(([outlet, products]) => (
              <div key={outlet} className="outlet-section">
                <h3>{outlet}</h3>
                {products.map(product => (
                  <div key={product.id} className="product-card">
                    <div className="product-info">
                      <div className="product-name">{product.name}</div>
                      {product.brand && <div className="product-brand">{product.brand}</div>}
                      <div className="product-meta">
                        {product.distributor_name && <span>{product.distributor_name}</span>}
                        {product.pack && product.size && product.unit_abbreviation && (
                          <span> • {product.pack}pk × {product.size}{product.unit_abbreviation}</span>
                        )}
                      </div>
                    </div>
                    <div className="product-pricing">
                      {product.case_price != null && (
                        <>
                          <div className="price-case">${product.case_price.toFixed(2)}/cs</div>
                          {product.unit_price != null && (
                            <div className="price-unit">
                              ${product.unit_price.toFixed(2)}/{product.unit_abbreviation || 'unit'}
                            </div>
                          )}
                        </>
                      )}
                      {product.case_price == null && <div className="price-none">No price</div>}
                    </div>
                    <button className="btn-unmap" onClick={() => handleUnmap(product.id)}>
                      Unmap
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
