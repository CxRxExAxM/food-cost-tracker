import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import SignaturePad from './SignaturePad';
import { Check, FileText, ExternalLink } from 'lucide-react';
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
  const [signature, setSignature] = useState(null);
  const [newRowData, setNewRowData] = useState({});

  const columns = config?.columns || [];
  const rows = config?.rows || [];
  const introText = config?.intro_text || '';
  const propertyName = config?.property_name || 'Property';
  const documentPath = config?.document_path;

  // Get non-signature columns for data entry
  const dataColumns = columns.filter(c => c.type !== 'signature');
  const signatureColumn = columns.find(c => c.type === 'signature');
  const showResponses = config?.show_responses || false;

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

  const handleSignClick = (index) => {
    setActiveSigningIndex(activeSigningIndex === index ? null : index);
    setSignature(null);
  };

  const handleSubmit = (rowIndex) => {
    if (!signature || submitting) return;

    const row = rows[rowIndex];
    // Get the name from the first text column, or use a generic identifier
    const nameColumn = dataColumns.find(c => c.key === 'name') || dataColumns[0];
    const respondentName = row?.[nameColumn?.key] || `Row ${rowIndex + 1}`;

    onSubmit({
      respondent_name: respondentName,
      response_data: {
        row_index: rowIndex,
        row_data: row
      },
      signature_data: signature
    });

    setActiveSigningIndex(null);
    setSignature(null);
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
        <h1 className="form-title">Sign-off Form</h1>
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
              const isActive = activeSigningIndex === idx;

              return (
                <tr key={idx} className={isActive ? 'active-row' : ''}>
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
                            <button
                              type="button"
                              className={`btn-sign ${isActive ? 'active' : ''}`}
                              onClick={() => handleSignClick(idx)}
                            >
                              {isActive ? 'Cancel' : 'Sign'}
                            </button>
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

      {/* Inline Signature Area */}
      {activeSigningIndex !== null && (
        <div className="inline-signature-area">
          <div className="signing-for">
            Signing row: <strong>{activeSigningIndex + 1}</strong>
            {rows[activeSigningIndex]?.name && (
              <> — {rows[activeSigningIndex].name}</>
            )}
          </div>

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
    </div>
  );
}
