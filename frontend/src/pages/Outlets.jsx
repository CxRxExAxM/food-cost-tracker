import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useOutlet } from '../contexts/OutletContext';
import Navigation from '../components/Navigation';
import OrgCard from '../components/outlets/OrgCard';
import OutletCard from '../components/outlets/OutletCard';
import CreateOutletModal from '../components/outlets/CreateOutletModal';
import './Outlets.css';

export default function Outlets({ embedded = false }) {
  const { isAdmin } = useAuth();
  const { outlets, loading, fetchOutlets } = useOutlet();
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'

  // Fetch outlets on mount
  useEffect(() => {
    fetchOutlets();
  }, []);

  // Filter outlets based on search
  const filteredOutlets = outlets.filter(outlet => {
    const searchLower = searchTerm.toLowerCase();
    return (
      outlet.name?.toLowerCase().includes(searchLower) ||
      outlet.location?.toLowerCase().includes(searchLower) ||
      outlet.description?.toLowerCase().includes(searchLower)
    );
  });

  const handleCreateSuccess = () => {
    setShowCreateModal(false);
    fetchOutlets(); // Refresh list
  };

  return (
    <div className={`page-container ${embedded ? 'embedded' : ''}`}>
      {!embedded && <Navigation />}

      <div className="page-content">
        <div className="page-header">
          <div className="page-title-section">
            <h1 className="page-title">Outlets</h1>
            <p className="page-subtitle">
              Manage your organization's outlets and locations
            </p>
          </div>

          {isAdmin() && (
            <button
              className="btn btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              <span className="btn-icon">+</span>
              Create Outlet
            </button>
          )}
        </div>

        {/* Organization Overview Card */}
        <OrgCard />

        {/* Search and View Controls */}
        <div className="outlets-controls">
          <div className="search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search outlets..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            {searchTerm && (
              <button
                className="search-clear"
                onClick={() => setSearchTerm('')}
              >
                ✕
              </button>
            )}
          </div>

          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid view"
            >
              ▦
            </button>
            <button
              className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List view"
            >
              ☰
            </button>
          </div>
        </div>

        {/* Outlets Display */}
        {loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading outlets...</p>
          </div>
        ) : filteredOutlets.length === 0 ? (
          <div className="empty-state">
            {searchTerm ? (
              <>
                <span className="empty-icon">🔍</span>
                <h3>No outlets found</h3>
                <p>No outlets match your search: "{searchTerm}"</p>
                <button
                  className="btn btn-secondary"
                  onClick={() => setSearchTerm('')}
                >
                  Clear Search
                </button>
              </>
            ) : (
              <>
                <span className="empty-icon">🏢</span>
                <h3>No outlets yet</h3>
                <p>Get started by creating your first outlet</p>
                {isAdmin() && (
                  <button
                    className="btn btn-primary"
                    onClick={() => setShowCreateModal(true)}
                  >
                    <span className="btn-icon">+</span>
                    Create Outlet
                  </button>
                )}
              </>
            )}
          </div>
        ) : (
          <>
            <div className="outlets-stats">
              <span className="stats-text">
                {filteredOutlets.length} outlet{filteredOutlets.length !== 1 ? 's' : ''}
                {searchTerm && ` matching "${searchTerm}"`}
              </span>
            </div>

            <div className={`outlets-${viewMode}`}>
              {filteredOutlets.map((outlet) => (
                <OutletCard
                  key={outlet.id}
                  outlet={outlet}
                  viewMode={viewMode}
                  onUpdate={fetchOutlets}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Create Outlet Modal */}
      {showCreateModal && (
        <CreateOutletModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreateSuccess}
        />
      )}
    </div>
  );
}
