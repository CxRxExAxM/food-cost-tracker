/**
 * Outlet Pill Selector Component
 *
 * Reusable component for selecting outlets via pill/chip interface
 * Fetches from GET /api/ehc/outlets
 * Supports single-select and multi-select modes
 *
 * Usage:
 * <OutletPillSelector
 *   selected={selectedOutlets}
 *   onChange={handleOutletChange}
 *   multiSelect={true}
 * />
 */

import { useState, useEffect } from 'react';
import './OutletPillSelector.css';

const API_BASE = '/api/ehc';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

async function fetchWithAuth(url) {
  const response = await fetch(url, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error('Failed to fetch outlets');
  }
  return response.json();
}

export default function OutletPillSelector({
  selected = [],
  onChange,
  multiSelect = false,
  className = ''
}) {
  const [outlets, setOutlets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadOutlets();
  }, []);

  async function loadOutlets() {
    try {
      setLoading(true);
      const data = await fetchWithAuth(`${API_BASE}/outlets?active_only=true`);
      setOutlets(data.data || []);
      setError(null);
    } catch (err) {
      setError('Failed to load outlets');
    } finally {
      setLoading(false);
    }
  }

  function handlePillClick(outlet) {
    if (multiSelect) {
      // Multi-select mode: toggle outlet in array
      const isSelected = selected.some(s => s === outlet.name || s.name === outlet.name);
      if (isSelected) {
        onChange(selected.filter(s => (s.name || s) !== outlet.name));
      } else {
        onChange([...selected, outlet]);
      }
    } else {
      // Single-select mode: replace selection
      const isSelected = selected === outlet.name || selected?.name === outlet.name;
      onChange(isSelected ? null : outlet);
    }
  }

  function isSelected(outlet) {
    if (multiSelect) {
      return selected.some(s => (s === outlet.name) || (s.name === outlet.name));
    } else {
      return selected === outlet.name || selected?.name === outlet.name;
    }
  }

  // Group outlets by type
  const outletsByType = outlets.reduce((acc, outlet) => {
    const type = outlet.outlet_type || 'Other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(outlet);
    return acc;
  }, {});

  const typeOrder = ['Production Kitchen', 'Restaurant', 'Bar', 'Lounge', 'Support', 'Franchise', 'Other'];
  const sortedTypes = typeOrder.filter(type => outletsByType[type]);

  if (loading) {
    return <div className="outlet-pill-selector loading">Loading outlets...</div>;
  }

  if (error) {
    return <div className="outlet-pill-selector error">{error}</div>;
  }

  if (outlets.length === 0) {
    return <div className="outlet-pill-selector empty">No outlets configured</div>;
  }

  return (
    <div className={`outlet-pill-selector ${className}`}>
      {sortedTypes.map(type => (
        <div key={type} className="outlet-group">
          <div className="outlet-group-label">{type}</div>
          <div className="outlet-pills">
            {outletsByType[type].map(outlet => (
              <button
                key={outlet.id}
                type="button"
                className={`outlet-pill ${isSelected(outlet) ? 'selected' : ''}`}
                onClick={() => handlePillClick(outlet)}
                title={outlet.full_name || outlet.name}
              >
                {outlet.name}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
