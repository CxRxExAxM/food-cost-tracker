import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import axios from '../../lib/axios';
import './TokenManagerModal.css';

function TokenManagerModal({ onClose }) {
  const { user } = useAuth();
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newTokenLabel, setNewTokenLabel] = useState('');

  useEffect(() => {
    fetchTokens();
  }, []);

  const fetchTokens = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/waste/tokens');
      setTokens(response.data);
    } catch (error) {
      console.error('Error fetching tokens:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newTokenLabel.trim()) {
      alert('Please enter a label for the QR code');
      return;
    }

    setCreating(true);
    try {
      await axios.post('/waste/tokens', null, {
        params: { label: newTokenLabel }
      });
      setNewTokenLabel('');
      fetchTokens(); // Refresh list
    } catch (error) {
      console.error('Error creating token:', error);
      alert('Failed to create token');
    } finally {
      setCreating(false);
    }
  };

  const handleToggleActive = async (tokenId, currentStatus) => {
    try {
      await axios.put(`/waste/tokens/${tokenId}`, null, {
        params: { active: !currentStatus }
      });
      fetchTokens(); // Refresh list
    } catch (error) {
      console.error('Error updating token:', error);
      alert('Failed to update token');
    }
  };

  const handleDelete = async (tokenId) => {
    if (!confirm('Delete this QR code? All associated weigh-ins will also be deleted.')) {
      return;
    }

    try {
      await axios.delete(`/waste/tokens/${tokenId}`);
      fetchTokens(); // Refresh list
    } catch (error) {
      console.error('Error deleting token:', error);
      alert('Failed to delete token');
    }
  };

  const handleDownloadQR = (token) => {
    const base64 = token.qr_code_base64;
    if (!base64) return;

    const link = document.createElement('a');
    link.href = `data:image/png;base64,${base64}`;
    link.download = `waste-qr-${token.label.replace(/\s+/g, '-').toLowerCase()}.png`;
    link.click();
  };

  const handlePrintQR = (token) => {
    const base64 = token.qr_code_base64;
    if (!base64) return;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Print QR Code: ${token.label}</title>
          <style>
            body {
              margin: 0;
              padding: 40px;
              display: flex;
              flex-direction: column;
              align-items: center;
              font-family: Arial, sans-serif;
            }
            h1 {
              font-size: 32px;
              margin-bottom: 20px;
            }
            img {
              max-width: 400px;
              border: 2px solid #333;
              padding: 20px;
              background: white;
            }
            p {
              margin-top: 20px;
              font-size: 18px;
              text-align: center;
              color: #666;
            }
            @media print {
              body { padding: 20px; }
            }
          </style>
        </head>
        <body>
          <h1>🌱 Waste Weigh-In</h1>
          <img src="data:image/png;base64,${base64}" alt="QR Code" />
          <p><strong>${token.label}</strong></p>
          <p>Scan to submit waste diversion weigh-ins</p>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content token-manager-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2>QR Code Manager</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Create New Token */}
          <section className="create-token-section">
            <h3>Create New QR Code</h3>
            <div className="create-token-form">
              <input
                type="text"
                value={newTokenLabel}
                onChange={(e) => setNewTokenLabel(e.target.value)}
                placeholder="e.g., Kitchen Station A, Donation Bin"
                maxLength={100}
                onKeyPress={(e) => e.key === 'Enter' && handleCreate()}
              />
              <button
                onClick={handleCreate}
                disabled={creating || !newTokenLabel.trim()}
                className="btn-create"
              >
                {creating ? 'Creating...' : 'Create QR Code'}
              </button>
            </div>
          </section>

          {/* Token List */}
          <section className="tokens-list-section">
            <h3>Existing QR Codes ({tokens.length})</h3>
            {loading ? (
              <div className="loading-message">Loading tokens...</div>
            ) : tokens.length === 0 ? (
              <div className="empty-message">
                No QR codes yet. Create one above to get started.
              </div>
            ) : (
              <div className="tokens-grid">
                {tokens.map((token) => (
                  <div key={token.id} className={`token-card ${!token.active ? 'inactive' : ''}`}>
                    <div className="token-qr">
                      {token.qr_code_base64 && (
                        <img
                          src={`data:image/png;base64,${token.qr_code_base64}`}
                          alt={`QR Code: ${token.label}`}
                        />
                      )}
                    </div>
                    <div className="token-info">
                      <div className="token-label">{token.label}</div>
                      <div className="token-status">
                        {token.active ? (
                          <span className="status-badge active">Active</span>
                        ) : (
                          <span className="status-badge inactive">Inactive</span>
                        )}
                      </div>
                      <div className="token-date">
                        Created: {new Date(token.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="token-actions">
                      <button
                        className="btn-icon"
                        onClick={() => handleDownloadQR(token)}
                        title="Download QR Code"
                      >
                        📥
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handlePrintQR(token)}
                        title="Print QR Code"
                      >
                        🖨️
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handleToggleActive(token.id, token.active)}
                        title={token.active ? 'Deactivate' : 'Activate'}
                      >
                        {token.active ? '⏸️' : '▶️'}
                      </button>
                      <button
                        className="btn-icon btn-danger"
                        onClick={() => handleDelete(token.id)}
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default TokenManagerModal;
