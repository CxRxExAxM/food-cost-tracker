import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import SignaturePad from './SignaturePad';
import { Check, FileText, ExternalLink, Plus, X, Pencil } from 'lucide-react';
import './TableSignoffForm.css';

/**
 * Table Sign-off Form (Dynamic columns)
 *
 * Features:
 * - Dynamic columns from config
 * - Pre-filled rows OR self-fill mode
 * - Each row has sign button that expands signature pad inline
 * - Shows completion status (signed/awaiting)
 * - Optional PDF document display
 */
export default function TableSignoffForm({
  config,
  title,
  existingResponses = [],
  onSubmit,
  submitting = false
}) {
  const { token } = useParams();
  const [activeSigningIndex, setActiveSigningIndex] = useState(null);
  const [selectedRowIndex, setSelectedRowIndex] = useState(null); // Row selected but not yet signing
  const [signature, setSignature] = useState(null);
  const [newRowData, setNewRowData] = useState({});
  // Track user edits for editable columns in pre-filled rows
  const [rowEdits, setRowEdits] = useState({});
  // For "Add New Entry" in pre-filled mode
  const [showAddNew, setShowAddNew] = useState(false);
  const [newEntrySignature, setNewEntrySignature] = useState(null);

  const columns = config?.columns || [];
  const rows = config?.rows || [];
  const introText = config?.intro_text || '';
  const propertyName = config?.property_name || 'Property';
  const documentPath = config?.document_path;

  // Get non-signature columns for data entry
  const dataColumns = columns.filter(c => c.type !== 'signature');
  const signatureColumn = columns.find(c => c.type === 'signature');
  const showResponses = config?.show_responses || false;

  // Separate editable vs read-only columns for pre-filled rows
  const editableColumns = dataColumns.filter(c => c.editable);
  const readOnlyColumns = dataColumns.filter(c => !c.editable);

  // Map existing responses to row indices
  const signedIndices = useMemo(() => {
    const map = new Map();
    existingResponses.forEach(resp => {
      if (resp.response_data?.row_index !== undefined) {
        map.set(resp.response_data.row_index, resp);
      }
    });
    return map;
  }, [existingResponses]);

  // Handle row tap/click - select row and show floating bar
  const handleRowSelect = (index) => {
    const isSigned = signedIndices.has(index);
    if (isSigned) return; // Can't select signed rows

    if (selectedRowIndex === index) {
      // Tapping same row deselects
      setSelectedRowIndex(null);
    } else {
      setSelectedRowIndex(index);
      // Close signing area if open for different row
      if (activeSigningIndex !== null && activeSigningIndex !== index) {
        setActiveSigningIndex(null);
        setSignature(null);
        setRowEdits({});
      }
    }
  };

  // Start signing the selected row
  const handleStartSigning = () => {
    if (selectedRowIndex === null) return;

    setActiveSigningIndex(selectedRowIndex);
    setSignature(null);
    // Pre-populate with any existing values from the row
    const row = rows[selectedRowIndex] || {};
    const initialEdits = {};
    editableColumns.forEach(col => {
      initialEdits[col.key] = row[col.key] || '';
    });
    setRowEdits(initialEdits);
  };

  // Cancel signing
  const handleCancelSigning = () => {
    setActiveSigningIndex(null);
    setSelectedRowIndex(null);
    setSignature(null);
    setRowEdits({});
  };

  // Legacy handler for backwards compatibility
  const handleSignClick = (index) => {
    if (activeSigningIndex === index) {
      handleCancelSigning();
    } else {
      setSelectedRowIndex(index);
      setActiveSigningIndex(index);
      setSignature(null);
      const row = rows[index] || {};
      const initialEdits = {};
      editableColumns.forEach(col => {
        initialEdits[col.key] = row[col.key] || '';
      });
      setRowEdits(initialEdits);
    }
  };

  const handleSubmit = (rowIndex) => {
    if (!signature || submitting) return;

    // Check required editable fields are filled
    const missingRequired = editableColumns
      .filter(c => c.required && !rowEdits[c.key]?.trim())
      .map(c => c.label);
    if (missingRequired.length > 0) {
      alert(`Please fill in: ${missingRequired.join(', ')}`);
      return;
    }

    const row = rows[rowIndex];
    // Merge original row data with user edits
    const mergedRowData = { ...row, ...rowEdits };

    // Get the name from edits first (if name is editable), then fall back to row data
    const nameColumn = dataColumns.find(c => c.key === 'name') || dataColumns[0];
    const respondentName = rowEdits[nameColumn?.key]?.trim() || row?.[nameColumn?.key] || `Row ${rowIndex + 1}`;

    onSubmit({
      respondent_name: respondentName,
      response_data: {
        row_index: rowIndex,
        row_data: mergedRowData
      },
      signature_data: signature
    });

    setActiveSigningIndex(null);
    setSignature(null);
    setRowEdits({});
  };

  // For self-fill mode (no pre-filled rows)
  const handleSelfFillSubmit = () => {
    if (!signature || submitting) return;

    const nameColumn = dataColumns.find(c => c.key === 'name') || dataColumns[0];
    const respondentName = newRowData[nameColumn?.key] || 'Unknown';

    onSubmit({
      respondent_name: respondentName,
      response_data: {
        row_index: -1, // Indicates self-filled
        row_data: newRowData
      },
      signature_data: signature
    });

    setNewRowData({});
    setSignature(null);
  };

  // For "Add New Entry" in pre-filled mode
  const handleAddNewSubmit = () => {
    if (!newEntrySignature || submitting) return;

    // Check required fields
    const missingRequired = dataColumns
      .filter(c => c.required && !newRowData[c.key]?.trim())
      .map(c => c.label);
    if (missingRequired.length > 0) {
      alert(`Please fill in: ${missingRequired.join(', ')}`);
      return;
    }

    const nameColumn = dataColumns.find(c => c.key === 'name') || dataColumns[0];
    const respondentName = newRowData[nameColumn?.key] || 'New Entry';

    onSubmit({
      respondent_name: respondentName,
      response_data: {
        row_index: -1, // Indicates user-added entry
        row_data: newRowData
      },
      signature_data: newEntrySignature
    });

    setNewRowData({});
    setNewEntrySignature(null);
    setShowAddNew(false);
  };

  const allSigned = rows.length > 0 &&
    rows.every((_, idx) => signedIndices.has(idx));

  // Self-fill mode: no pre-filled rows
  if (rows.length === 0) {
    return (
      <div className="table-signoff-form">
        {/* Header */}
        <div className="form-header">
          <h1 className="form-title">{title || 'Sign-off Form'}</h1>
          <div className="form-meta">
            <span>{propertyName}</span>
          </div>
        </div>

        {/* Intro */}
        {introText && (
          <div className="form-intro">
            <p>{introText}</p>
          </div>
        )}

        {/* PDF Document */}
        {documentPath && (
          <a
            href={`/api/ehc/forms/${token}/document`}
            target="_blank"
            rel="noopener noreferrer"
            className="view-document-btn"
          >
            <FileText size={18} />
            <span>View Reference Document</span>
            <ExternalLink size={16} />
          </a>
        )}

        {/* Response count */}
        <div className="response-count">
          {existingResponses.length} response{existingResponses.length !== 1 ? 's' : ''} collected
        </div>

        {/* Existing Responses List (if enabled) */}
        {showResponses && existingResponses.length > 0 && (
          <div className="responses-list">
            <h4>Registered Items</h4>
            <ul>
              {existingResponses.map((resp, idx) => {
                const rowData = resp.response_data?.row_data || {};
                // Display first few data columns
                const displayValues = dataColumns
                  .slice(0, 3)
                  .map(col => rowData[col.key])
                  .filter(Boolean)
                  .join(' — ');
                return (
                  <li key={idx}>
                    <Check size={14} />
                    <span>{resp.respondent_name || displayValues || `Entry ${idx + 1}`}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Self-fill form */}
        <div className="self-fill-form">
          <h3>Enter your information</h3>
          {dataColumns.map(col => (
            <div key={col.key} className="form-field">
              <label>{col.label}{col.required && ' *'}</label>
              {col.type === 'date' ? (
                <input
                  type="date"
                  value={newRowData[col.key] || ''}
                  onChange={e => setNewRowData({ ...newRowData, [col.key]: e.target.value })}
                />
              ) : (
                <input
                  type="text"
                  value={newRowData[col.key] || ''}
                  onChange={e => setNewRowData({ ...newRowData, [col.key]: e.target.value })}
                  placeholder={col.label}
                />
              )}
            </div>
          ))}

          <div className="signature-section">
            <label>{signatureColumn?.label || 'Signature'}</label>
            <SignaturePad onSignatureChange={setSignature} />
          </div>

          <button
            type="button"
            className="btn-submit-signature"
            disabled={!signature || submitting || !dataColumns.every(c => !c.required || newRowData[c.key]?.trim())}
            onClick={handleSelfFillSubmit}
          >
            {submitting ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>
    );
  }

  // Pre-filled rows mode
  return (
    <div className="table-signoff-form">
      {/* Header */}
      <div className="form-header">
        <h1 className="form-title">{title || 'Sign-off Form'}</h1>
        <div className="form-meta">
          <span>{propertyName}</span>
        </div>
      </div>

      {/* Intro */}
      {introText && (
        <div className="form-intro">
          <p>{introText}</p>
        </div>
      )}

      {/* PDF Document */}
      {documentPath && (
        <a
          href={`/api/ehc/forms/${token}/document`}
          target="_blank"
          rel="noopener noreferrer"
          className="view-document-btn"
        >
          <FileText size={18} />
          <span>View Reference Document</span>
          <ExternalLink size={16} />
        </a>
      )}

      {/* Completion Banner */}
      {allSigned && (
        <div className="completion-banner">
          <Check size={20} />
          <span>All rows have been signed</span>
        </div>
      )}

      {/* Progress */}
      <div className="roster-progress">
        <span className="progress-count">
          {signedIndices.size} of {rows.length} signed
        </span>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(signedIndices.size / rows.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Table */}
      <div className="table-signoff-container">
        <table className="signoff-table">
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col.key}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const existingResponse = signedIndices.get(idx);
              const isSigned = !!existingResponse;
              const isSelected = selectedRowIndex === idx;
              const isActive = activeSigningIndex === idx;

              return (
                <tr
                  key={idx}
                  className={`${isSelected ? 'selected-row' : ''} ${isActive ? 'active-row' : ''} ${isSigned ? 'signed-row' : 'unsigned-row'}`}
                  onClick={() => !isSigned && handleRowSelect(idx)}
                >
                  {columns.map(col => {
                    if (col.type === 'signature') {
                      return (
                        <td key={col.key} className="signature-cell">
                          {isSigned ? (
                            <div className="signed-indicator">
                              <Check size={16} />
                              <span>Signed</span>
                            </div>
                          ) : (
                            <div className="status-indicator">
                              <span>{isSelected ? 'Selected' : 'Tap row'}</span>
                            </div>
                          )}
                        </td>
                      );
                    }

                    // Data column
                    const value = row[col.key];
                    if (col.type === 'date' && value) {
                      return (
                        <td key={col.key}>
                          {new Date(value).toLocaleDateString()}
                        </td>
                      );
                    }
                    return <td key={col.key}>{value || '—'}</td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Floating Sign Bar - appears when row is selected but not yet signing */}
      {selectedRowIndex !== null && activeSigningIndex === null && (
        <div className="floating-sign-bar">
          <div className="floating-bar-content">
            <div className="selected-row-info">
              <span className="row-number">Row {selectedRowIndex + 1}</span>
              {/* Show first few column values for context */}
              {readOnlyColumns.slice(0, 2).map(col => {
                const value = rows[selectedRowIndex]?.[col.key];
                return value ? (
                  <span key={col.key} className="row-preview">{value}</span>
                ) : null;
              })}
            </div>
            <div className="floating-bar-actions">
              <button
                type="button"
                className="btn-cancel-select"
                onClick={() => setSelectedRowIndex(null)}
              >
                <X size={18} />
              </button>
              <button
                type="button"
                className="btn-sign-now"
                onClick={handleStartSigning}
              >
                <Pencil size={16} />
                <span>Sign Now</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inline Signature Area */}
      {activeSigningIndex !== null && (
        <div className="inline-signature-area">
          <div className="signing-for">
            Signing row: <strong>{activeSigningIndex + 1}</strong>
            {/* Show read-only values for context */}
            {readOnlyColumns.map(col => {
              const value = rows[activeSigningIndex]?.[col.key];
              return value ? <span key={col.key}> — {value}</span> : null;
            })}
          </div>

          {/* Editable Fields */}
          {editableColumns.length > 0 && (
            <div className="editable-fields">
              {editableColumns.map(col => (
                <div key={col.key} className="editable-field">
                  <label>{col.label}{col.required && ' *'}</label>
                  {col.type === 'date' ? (
                    <input
                      type="date"
                      value={rowEdits[col.key] || ''}
                      onChange={e => setRowEdits({ ...rowEdits, [col.key]: e.target.value })}
                    />
                  ) : (
                    <input
                      type="text"
                      value={rowEdits[col.key] || ''}
                      onChange={e => setRowEdits({ ...rowEdits, [col.key]: e.target.value })}
                      placeholder={`Enter ${col.label.toLowerCase()}`}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          <SignaturePad onSignatureChange={setSignature} />

          <button
            type="button"
            className="btn-submit-signature"
            disabled={!signature || submitting}
            onClick={() => handleSubmit(activeSigningIndex)}
          >
            {submitting ? 'Submitting...' : 'Submit Signature'}
          </button>
        </div>
      )}

      {/* Spacer when floating bar is visible to prevent content overlap */}
      {selectedRowIndex !== null && activeSigningIndex === null && (
        <div className="floating-bar-spacer" style={{ height: '80px' }} />
      )}

      {/* Add New Entry Section */}
      {activeSigningIndex === null && (
        <div className="add-new-entry-section">
          {!showAddNew ? (
            <button
              type="button"
              className="btn-add-new-entry"
              onClick={() => setShowAddNew(true)}
            >
              <Plus size={18} />
              <span>Location not listed? Add new entry</span>
            </button>
          ) : (
            <div className="add-new-entry-form">
              <div className="add-new-header">
                <h4>Add New Entry</h4>
                <button
                  type="button"
                  className="btn-cancel-add"
                  onClick={() => {
                    setShowAddNew(false);
                    setNewRowData({});
                    setNewEntrySignature(null);
                  }}
                >
                  Cancel
                </button>
              </div>

              <p className="add-new-hint">
                Fill in all fields below to register an item not in the list above.
              </p>

              <div className="add-new-fields">
                {dataColumns.map(col => (
                  <div key={col.key} className="form-field">
                    <label>{col.label}{col.required && ' *'}</label>
                    {col.type === 'date' ? (
                      <input
                        type="date"
                        value={newRowData[col.key] || ''}
                        onChange={e => setNewRowData({ ...newRowData, [col.key]: e.target.value })}
                      />
                    ) : (
                      <input
                        type="text"
                        value={newRowData[col.key] || ''}
                        onChange={e => setNewRowData({ ...newRowData, [col.key]: e.target.value })}
                        placeholder={`Enter ${col.label.toLowerCase()}`}
                      />
                    )}
                  </div>
                ))}
              </div>

              <div className="signature-section">
                <label>{signatureColumn?.label || 'Signature'}</label>
                <SignaturePad onSignatureChange={setNewEntrySignature} />
              </div>

              <button
                type="button"
                className="btn-submit-signature"
                disabled={!newEntrySignature || submitting}
                onClick={handleAddNewSubmit}
              >
                {submitting ? 'Submitting...' : 'Submit New Entry'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
