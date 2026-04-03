/**
 * Sign-off Form Creation/Edit Modal
 *
 * Flexible form builder for any sign-off needs:
 * - Configure custom columns (text, date, signature)
 * - Optionally pre-fill rows
 * - Optionally attach a reference PDF
 * - Staff view form and sign
 *
 * Edit mode: Pass editingLink prop with existing form data
 */

import { useState, useEffect } from 'react';
import { API_BASE, fetchWithAuth } from '../tabs/shared';

const DEFAULT_COLUMNS = [
  { key: 'name', label: 'Name', type: 'text', required: true },
  { key: 'signature', label: 'Signature', type: 'signature', required: true }
];

const COLUMN_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'date', label: 'Date' },
  { value: 'signature', label: 'Signature' }
];

export default function TableSignoffModal({
  isOpen,
  onClose,
  activeCycle,
  records,
  onFormCreated,
  editingLink,  // Optional: existing form link data for edit mode
  toast
}) {
  const isEditMode = !!editingLink;

  const [step, setStep] = useState(1); // 1: Select record, 2: Configure form, 3: Add rows
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [title, setTitle] = useState('');
  const [introText, setIntroText] = useState('');
  const [columns, setColumns] = useState([...DEFAULT_COLUMNS]);
  const [rows, setRows] = useState([]);
  const [expectedResponses, setExpectedResponses] = useState('');
  const [creating, setCreating] = useState(false);

  // PDF upload state
  const [pdfFile, setPdfFile] = useState(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [uploadedPdfPath, setUploadedPdfPath] = useState(null);
  const [existingPdfName, setExistingPdfName] = useState(null);

  // Reset/populate state when modal opens
  useEffect(() => {
    if (isOpen) {
      if (editingLink) {
        // Edit mode: populate from existing data
        setStep(2); // Skip record selection
        setSelectedRecord({
          id: editingLink.record_id,
          record_number: editingLink.record_number,
          name: editingLink.record_name
        });
        setTitle(editingLink.title || '');
        setIntroText(editingLink.config?.intro_text || '');
        setColumns(editingLink.config?.columns || [...DEFAULT_COLUMNS]);
        setRows(editingLink.config?.rows || []);
        setExpectedResponses(editingLink.expected_responses?.toString() || '');

        // Handle existing PDF
        if (editingLink.config?.document_path) {
          setUploadedPdfPath(editingLink.config.document_path);
          // Extract filename from path
          const pathParts = editingLink.config.document_path.split('/');
          setExistingPdfName(pathParts[pathParts.length - 1]);
        } else {
          setUploadedPdfPath(null);
          setExistingPdfName(null);
        }
        setPdfFile(null);
      } else {
        // Create mode: reset to defaults
        setStep(1);
        setSelectedRecord(null);
        setTitle('');
        setIntroText('');
        setColumns([...DEFAULT_COLUMNS]);
        setRows([]);
        setExpectedResponses('');
        setPdfFile(null);
        setUploadedPdfPath(null);
        setExistingPdfName(null);
      }
    }
  }, [isOpen, editingLink]);

  function addColumn() {
    const newKey = `col_${columns.length}`;
    setColumns([...columns, { key: newKey, label: '', type: 'text', required: false }]);
  }

  function removeColumn(index) {
    if (columns[index].type === 'signature') {
      toast?.error?.('Cannot remove the signature column');
      return;
    }
    setColumns(columns.filter((_, i) => i !== index));
  }

  function updateColumn(index, field, value) {
    setColumns(columns.map((col, i) =>
      i === index ? { ...col, [field]: value } : col
    ));
  }

  function moveColumn(index, direction) {
    if (
      (direction === -1 && index === 0) ||
      (direction === 1 && index === columns.length - 1)
    ) return;

    const newColumns = [...columns];
    const temp = newColumns[index];
    newColumns[index] = newColumns[index + direction];
    newColumns[index + direction] = temp;
    setColumns(newColumns);
  }

  function addRow() {
    const emptyRow = {};
    columns.forEach(col => {
      if (col.type !== 'signature') {
        emptyRow[col.key] = '';
      }
    });
    setRows([...rows, emptyRow]);
  }

  function removeRow(index) {
    setRows(rows.filter((_, i) => i !== index));
  }

  function updateRow(rowIndex, key, value) {
    setRows(rows.map((row, i) =>
      i === rowIndex ? { ...row, [key]: value } : row
    ));
  }

  async function handlePdfSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      toast?.error?.('Please select a PDF file');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast?.error?.('File size must be under 10MB');
      return;
    }

    setPdfFile(file);

    // Upload immediately
    try {
      setUploadingPdf(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/form-links/upload-document`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      setUploadedPdfPath(data.document_path);
      toast?.success?.('PDF uploaded');
    } catch (error) {
      toast?.error?.('Failed to upload PDF');
      setPdfFile(null);
    } finally {
      setUploadingPdf(false);
    }
  }

  function removePdf() {
    setPdfFile(null);
    setUploadedPdfPath(null);
    setExistingPdfName(null);
  }

  async function handleSubmit() {
    const validColumns = columns.filter(c => c.label.trim());
    if (validColumns.length < 2) {
      toast?.error?.('Add at least 2 columns (including signature)');
      return;
    }

    if (!validColumns.some(c => c.type === 'signature')) {
      toast?.error?.('A signature column is required');
      return;
    }

    try {
      setCreating(true);

      const config = {
        columns: validColumns,
        rows: rows,
        intro_text: introText,
        document_path: uploadedPdfPath,
        property_name: 'Fairmont Scottsdale Princess' // TODO: Get from org settings
      };

      // Determine expected responses: use explicit value, fall back to row count, or null
      const expResp = expectedResponses
        ? parseInt(expectedResponses)
        : (rows.length > 0 ? rows.length : null);

      if (isEditMode) {
        // PATCH existing form link
        const payload = {
          title: title || `${selectedRecord.name} - EHC ${activeCycle.year}`,
          config,
          expected_responses: expResp
        };

        await fetchWithAuth(`${API_BASE}/form-links/${editingLink.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload)
        });

        toast?.success?.('Form updated successfully');
      } else {
        // POST new form link
        const payload = {
          form_type: 'table_signoff',
          record_id: selectedRecord.id,
          title: title || `${selectedRecord.name} - EHC ${activeCycle.year}`,
          config,
          expected_responses: expResp
        };

        await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/form-links`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });

        toast?.success?.('Form created successfully');
      }

      onFormCreated?.();
      onClose();
    } catch (error) {
      toast?.error?.(error.message || `Failed to ${isEditMode ? 'update' : 'create'} form`);
    } finally {
      setCreating(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content form-create-modal extra-wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEditMode ? 'Edit Sign-off Form' : 'Create Sign-off Form'}</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {/* Step 1: Select Record */}
        {step === 1 && (
          <div className="modal-body">
            <p className="modal-description">
              Select which EHC record this form is for.
            </p>

            <div className="record-select-list">
              {records?.map(record => (
                <div
                  key={record.id}
                  className={`record-option ${selectedRecord?.id === record.id ? 'selected' : ''}`}
                  onClick={() => setSelectedRecord(record)}
                >
                  <span className="record-number">{record.record_number}</span>
                  <span className="record-name">{record.name}</span>
                </div>
              ))}
            </div>

            <div className="modal-actions">
              <button className="btn-ghost" onClick={onClose}>Cancel</button>
              <button
                className="btn-primary"
                onClick={() => setStep(2)}
                disabled={!selectedRecord}
              >
                Next: Configure Form
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Configure Form */}
        {step === 2 && (
          <div className="modal-body">
            <div className="selected-record-banner">
              <span className="record-number">{selectedRecord.record_number}</span>
              <span className="record-name">{selectedRecord.name}</span>
              {!isEditMode && (
                <button className="btn-link" onClick={() => setStep(1)}>Change</button>
              )}
            </div>

            <div className="form-field">
              <label>Form Title (optional)</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder={`${selectedRecord.name} - EHC ${activeCycle.year}`}
              />
            </div>

            <div className="form-field">
              <label>Introduction Text (optional)</label>
              <textarea
                value={introText}
                onChange={e => setIntroText(e.target.value)}
                placeholder="Instructions shown at the top of the form..."
                rows={2}
              />
            </div>

            {/* PDF Upload */}
            <div className="form-field">
              <label>Reference Document (optional)</label>
              <p className="field-hint">
                Attach a PDF that staff should review before signing.
              </p>
              {pdfFile ? (
                <div className="uploaded-file">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{pdfFile.name}</span>
                  <span className="file-size">
                    {uploadingPdf ? 'Uploading...' : `${(pdfFile.size / 1024).toFixed(0)} KB`}
                  </span>
                  <button
                    className="btn-icon danger"
                    onClick={removePdf}
                    disabled={uploadingPdf}
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              ) : existingPdfName ? (
                <div className="uploaded-file">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{existingPdfName}</span>
                  <span className="file-size existing">Attached</span>
                  <button
                    className="btn-icon danger"
                    onClick={removePdf}
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <div className="file-upload-area">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handlePdfSelect}
                  />
                  <span className="file-upload-label">
                    Click or drag to upload PDF
                  </span>
                </div>
              )}
            </div>

            <div className="form-field">
              <label>Table Columns</label>
              <div className="columns-editor">
                <div className="columns-header">
                  <span></span>
                  <span>Column Label</span>
                  <span>Type</span>
                  <span></span>
                </div>
                {columns.map((col, index) => (
                  <div key={index} className="column-row">
                    <button
                      className="btn-icon move"
                      onClick={() => moveColumn(index, -1)}
                      disabled={index === 0}
                      title="Move up"
                    >
                      ↑
                    </button>
                    <button
                      className="btn-icon move"
                      onClick={() => moveColumn(index, 1)}
                      disabled={index === columns.length - 1}
                      title="Move down"
                    >
                      ↓
                    </button>
                    <input
                      type="text"
                      value={col.label}
                      onChange={e => updateColumn(index, 'label', e.target.value)}
                      placeholder="Column label"
                      className="column-label-input"
                    />
                    <select
                      value={col.type}
                      onChange={e => updateColumn(index, 'type', e.target.value)}
                      className="column-type-select"
                    >
                      {COLUMN_TYPES.map(t => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                    <button
                      className="btn-icon danger"
                      onClick={() => removeColumn(index)}
                      disabled={col.type === 'signature'}
                      title="Remove column"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button className="btn-add-member" onClick={addColumn}>
                  + Add Column
                </button>
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setStep(1)}>Back</button>
              <button
                className="btn-primary"
                onClick={() => setStep(3)}
                disabled={!columns.some(c => c.label.trim())}
              >
                Next: Pre-fill Rows (Optional)
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Pre-fill Rows */}
        {step === 3 && (
          <div className="modal-body">
            <div className="selected-record-banner">
              <span className="record-number">{selectedRecord.record_number}</span>
              <span className="record-name">{selectedRecord.name}</span>
              <button className="btn-link" onClick={() => setStep(2)}>Edit form</button>
            </div>

            <div className="form-field">
              <label>Pre-filled Rows (optional)</label>
              <p className="field-hint">
                Add rows with pre-filled data. Staff will find their row and sign.
                Leave empty to let respondents fill in their own information.
              </p>

              {rows.length > 0 && (
                <div className="rows-editor">
                  <div className="rows-header">
                    {columns.filter(c => c.type !== 'signature').map(col => (
                      <span key={col.key}>{col.label}</span>
                    ))}
                    <span></span>
                  </div>
                  {rows.map((row, rowIndex) => (
                    <div key={rowIndex} className="row-entry">
                      {columns.filter(c => c.type !== 'signature').map(col => (
                        <input
                          key={col.key}
                          type={col.type === 'date' ? 'date' : 'text'}
                          value={row[col.key] || ''}
                          onChange={e => updateRow(rowIndex, col.key, e.target.value)}
                          placeholder={col.label}
                        />
                      ))}
                      <button
                        className="btn-icon danger"
                        onClick={() => removeRow(rowIndex)}
                        title="Remove row"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <button className="btn-add-member" onClick={addRow}>
                + Add Row
              </button>
            </div>

            {/* Expected Responses (in edit mode, show explicitly) */}
            {isEditMode && (
              <div className="form-field">
                <label>Expected Responses (optional)</label>
                <input
                  type="number"
                  value={expectedResponses}
                  onChange={e => setExpectedResponses(e.target.value)}
                  placeholder="Leave empty for unlimited"
                  min="1"
                  style={{ maxWidth: '200px' }}
                />
                <p className="field-hint">
                  If set, a progress bar shows completion status.
                </p>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setStep(2)}>Back</button>
              <button
                className="btn-primary"
                onClick={handleSubmit}
                disabled={creating}
              >
                {creating
                  ? (isEditMode ? 'Saving...' : 'Creating...')
                  : (isEditMode ? 'Save Changes' : 'Create Form')
                }
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
