import { useState, useEffect } from 'react';
import { parseRecipeFile, getUsageStats } from '../../services/aiParseService';
import './RecipeImport.css';

export default function UploadRecipeModal({ isOpen, onClose, outletId, onParseComplete }) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [usageStats, setUsageStats] = useState(null);

  // Load usage stats when modal opens
  useEffect(() => {
    if (isOpen) {
      loadUsageStats();
    }
  }, [isOpen]);

  const loadUsageStats = async () => {
    try {
      const stats = await getUsageStats();
      setUsageStats(stats.current_month);
    } catch (err) {
      console.error('Error loading usage stats:', err);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    validateAndSetFile(droppedFile);
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    validateAndSetFile(selectedFile);
  };

  const validateAndSetFile = (selectedFile) => {
    if (!selectedFile) return;

    // Check file extension
    const validExtensions = ['.docx', '.pdf', '.xlsx'];
    const fileExt = selectedFile.name.toLowerCase().slice(selectedFile.name.lastIndexOf('.'));

    if (!validExtensions.includes(fileExt)) {
      setError(`Invalid file type. Supported: ${validExtensions.join(', ')}`);
      return;
    }

    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (selectedFile.size > maxSize) {
      setError('File size exceeds 10MB limit');
      return;
    }

    setFile(selectedFile);
    setError(null);
  };

  const handleParseRecipe = async () => {
    if (!file) return;

    setProcessing(true);
    setError(null);

    try {
      // Progress updates
      setProgress('Uploading file...');

      await new Promise(resolve => setTimeout(resolve, 500));
      setProgress('Analyzing document...');

      const result = await parseRecipeFile(file, outletId);

      setProgress('Extracting ingredients...');
      await new Promise(resolve => setTimeout(resolve, 300));

      setProgress('Matching products...');
      await new Promise(resolve => setTimeout(resolve, 300));

      setProgress('Complete!');

      // Call parent callback with results
      onParseComplete(result);

      // Close modal
      setTimeout(() => {
        onClose();
        resetState();
      }, 500);

    } catch (err) {
      console.error('Parse error:', err);

      // Handle different error types
      if (err.response?.status === 429) {
        setError(err.response.data.detail || 'Upload limit exceeded. Please try again later.');
      } else if (err.response?.status === 400) {
        setError(err.response.data.detail || 'Invalid file or could not extract recipe');
      } else {
        setError('Failed to parse recipe. Please try again or contact support.');
      }

      setProcessing(false);
      setProgress('');
    }
  };

  const resetState = () => {
    setFile(null);
    setProcessing(false);
    setProgress('');
    setError(null);
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content upload-recipe-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Recipe Document</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {!processing ? (
            <>
              {/* Drag & Drop Zone */}
              <div
                className={`dropzone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input').click()}
              >
                <input
                  id="file-input"
                  type="file"
                  accept=".docx,.pdf,.xlsx"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />

                {!file ? (
                  <>
                    <div className="dropzone-icon">📄</div>
                    <p className="dropzone-text">Drag & drop file here</p>
                    <p className="dropzone-subtext">or click to browse</p>
                    <p className="dropzone-formats">Supported: .docx, .pdf, .xlsx</p>
                  </>
                ) : (
                  <>
                    <div className="dropzone-icon">✓</div>
                    <p className="dropzone-filename">{file.name}</p>
                    <p className="dropzone-filesize">{formatFileSize(file.size)}</p>
                    <button
                      className="change-file-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                    >
                      Change File
                    </button>
                  </>
                )}
              </div>

              {/* Usage Stats */}
              {usageStats && (
                <div className="usage-stats">
                  <div className="usage-label">
                    Usage: {usageStats.used}/{usageStats.limit} parses this month
                  </div>
                  <div className="usage-bar">
                    <div
                      className="usage-bar-fill"
                      style={{
                        width: `${(usageStats.used / (usageStats.limit === 'unlimited' ? 100 : usageStats.limit)) * 100}%`
                      }}
                    />
                  </div>
                  {usageStats.remaining !== 'unlimited' && usageStats.remaining <= 2 && (
                    <div className="usage-warning">
                      ⚠️ Only {usageStats.remaining} parses remaining this month
                    </div>
                  )}
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="error-message">
                  <span className="error-icon">⚠️</span>
                  {error}
                </div>
              )}
            </>
          ) : (
            /* Processing State */
            <div className="processing-state">
              <div className="spinner"></div>
              <h3>Parsing Recipe...</h3>
              <div className="progress-steps">
                {['Uploading file...', 'Analyzing document...', 'Extracting ingredients...', 'Matching products...', 'Complete!'].map((step, idx) => (
                  <div key={idx} className={`progress-step ${progress === step ? 'active' : ''} ${['Uploading file...', 'Analyzing document...', 'Extracting ingredients...', 'Matching products...'].indexOf(progress) > idx ? 'completed' : ''}`}>
                    {['Uploading file...', 'Analyzing document...', 'Extracting ingredients...', 'Matching products...'].indexOf(progress) > idx ? '✓' : idx === ['Uploading file...', 'Analyzing document...', 'Extracting ingredients...', 'Matching products...', 'Complete!'].indexOf(progress) ? '→' : ''} {step}
                  </div>
                ))}
              </div>
              <p className="processing-note">This usually takes 10-15 seconds</p>
            </div>
          )}
        </div>

        {!processing && (
          <div className="modal-actions">
            <button className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              className="btn-primary"
              onClick={handleParseRecipe}
              disabled={!file || usageStats?.remaining === 0}
            >
              Parse Recipe →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
