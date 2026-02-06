import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { outletsAPI } from '../../services/api/outlets';
import EditOutletModal from './EditOutletModal';
import './OutletCard.css';

export default function OutletCard({ outlet, viewMode, onUpdate }) {
  const { isAdmin } = useAuth();
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Fetch outlet statistics
  useEffect(() => {
    fetchStats();
  }, [outlet.id]);

  const fetchStats = async () => {
    try {
      setLoadingStats(true);
      const response = await outletsAPI.getStats(outlet.id);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch outlet stats:', error);
      setStats({ products_count: 0, recipes_count: 0, users_count: 0 });
    } finally {
      setLoadingStats(false);
    }
  };

  const handleDelete = async () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      return;
    }

    try {
      setDeleting(true);
      await outletsAPI.delete(outlet.id);
      onUpdate(); // Refresh the list
    } catch (error) {
      console.error('Failed to delete outlet:', error);
      alert(error.response?.data?.detail || 'Failed to delete outlet');
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleEditSuccess = () => {
    setShowEditModal(false);
    onUpdate(); // Refresh the list
  };

  return (
    <>
      <div className={`outlet-card outlet-card-${viewMode}`}>
        <div className="outlet-card-header">
          <div className="outlet-card-icon">🏢</div>
          <div className="outlet-card-info">
            <h3 className="outlet-card-name">{outlet.name}</h3>
            {outlet.location && (
              <p className="outlet-card-location">{outlet.location}</p>
            )}
          </div>
        </div>

        {outlet.description && (
          <p className="outlet-card-description">{outlet.description}</p>
        )}

        {/* Statistics */}
        <div className="outlet-card-stats">
          {loadingStats ? (
            <div className="stats-loading">Loading stats...</div>
          ) : (
            <>
              <div className="stat-item">
                <span className="stat-icon">📦</span>
                <div className="stat-info">
                  <span className="stat-value">{stats?.products_count || 0}</span>
                  <span className="stat-label">Products</span>
                </div>
              </div>

              <div className="stat-item">
                <span className="stat-icon">📋</span>
                <div className="stat-info">
                  <span className="stat-value">{stats?.recipes_count || 0}</span>
                  <span className="stat-label">Recipes</span>
                </div>
              </div>

              <div className="stat-item">
                <span className="stat-icon">👥</span>
                <div className="stat-info">
                  <span className="stat-value">{stats?.users_count || 0}</span>
                  <span className="stat-label">Users</span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Actions (Admin Only) */}
        {isAdmin() && (
          <div className="outlet-card-actions">
            <button
              className="btn-card btn-card-secondary"
              onClick={() => setShowEditModal(true)}
            >
              Edit
            </button>
            <button
              className={`btn-card btn-card-danger ${showDeleteConfirm ? 'confirm' : ''}`}
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : showDeleteConfirm ? 'Confirm Delete?' : 'Delete'}
            </button>
            {showDeleteConfirm && (
              <button
                className="btn-card btn-card-secondary"
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </button>
            )}
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <EditOutletModal
          outlet={outlet}
          onClose={() => setShowEditModal(false)}
          onSuccess={handleEditSuccess}
        />
      )}
    </>
  );
}
