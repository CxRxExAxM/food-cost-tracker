import { useState, useRef, useEffect } from 'react';
import { useOutlet } from '../../contexts/OutletContext';
import './OutletSelector.css';

export default function OutletSelector() {
  const { outlets, currentOutlet, loading, selectOutlet, isOrgWideAdmin } = useOutlet();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSelectOutlet = (outlet) => {
    selectOutlet(outlet);
    setIsOpen(false);
  };

  if (loading) {
    return (
      <div className="outlet-selector loading">
        <span>Loading outlets...</span>
      </div>
    );
  }

  if (outlets.length === 0) {
    return (
      <div className="outlet-selector empty">
        <span>No outlets available</span>
      </div>
    );
  }

  return (
    <div className="outlet-selector" ref={dropdownRef}>
      <button
        className="outlet-selector-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <span className="outlet-icon">🏢</span>
        <span className="outlet-name">
          {currentOutlet?.name || 'Select Outlet'}
        </span>
        <span className="outlet-dropdown-arrow">▼</span>
      </button>

      {isOpen && (
        <div className="outlet-dropdown">
          {isOrgWideAdmin() && (
            <>
              <button
                className={`outlet-dropdown-item ${
                  currentOutlet?.id === 'all' ? 'active' : ''
                }`}
                onClick={() => handleSelectOutlet({ id: 'all', name: 'All Outlets' })}
              >
                <span className="outlet-icon">🌐</span>
                <span>All Outlets</span>
                {currentOutlet?.id === 'all' && (
                  <span className="checkmark">✓</span>
                )}
              </button>
              <div className="outlet-dropdown-divider"></div>
            </>
          )}

          {outlets.map((outlet) => (
            <button
              key={outlet.id}
              className={`outlet-dropdown-item ${
                currentOutlet?.id === outlet.id ? 'active' : ''
              }`}
              onClick={() => handleSelectOutlet(outlet)}
            >
              <span className="outlet-icon">🏢</span>
              <div className="outlet-info">
                <span className="outlet-name-text">{outlet.name}</span>
                {outlet.location && (
                  <span className="outlet-location">{outlet.location}</span>
                )}
              </div>
              {currentOutlet?.id === outlet.id && (
                <span className="checkmark">✓</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
