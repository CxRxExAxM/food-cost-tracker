/**
 * Table Sign-off Form Creation Modal
 *
 * For custom table-based sign-off forms:
 * - Admin configures column definitions
 * - Admin optionally pre-fills rows
 * - Staff view table and sign their row
 * - PDF generated with same column structure
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
  toast
}) {
  const [step, setStep] = useState(1); // 1: Select record, 2: Configure columns, 3: Add rows
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [title, setTitle] = useState('');
  const [introText, setIntroText] = useState('');
  const [columns, setColumns] = useState([...DEFAULT_COLUMNS]);
  const [rows, setRows] = useState([]);
  const [creating, setCreating] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setSelectedRecord(null);
      setTitle('');
      setIntroText('');
      setColumns([...DEFAULT_COLUMNS]);
      setRows([]);
    }
  }, [isOpen]);

  function addColumn() {
    const newKey = `col_${columns.length}`;
    setColumns([...columns, { key: newKey, label: '', type: 'text', required: false }]);
  }

  function removeColumn(index) {
    // Don't allow removing the signature column
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

  async function handleCreate() {
    // Validate columns
    const validColumns = columns.filter(c => c.label.trim());
    if (validColumns.length < 2) {
      toast?.error?.('Add at least 2 columns (including signature)');
      return;
    }

    // Ensure there's a signature column
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
        property_name: 'Fairmont Scottsdale Princess' // TODO: Get from org settings
      };

      const payload = {
        form_type: 'table_signoff',
        record_id: selectedRecord.id,
        title: title || `${selectedRecord.name} - EHC ${activeCycle.year}`,
        config,
        expected_responses: rows.length > 0 ? rows.length : null
      };

      const data = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/form-links`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      toast?.success?.('Table sign-off form created');
      onFormCreated?.(data);
      onClose();
    } catch (error) {
      toast?.error?.(error.message || 'Failed to create form link');
    } finally {
      setCreating(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content form-create-modal wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Table Sign-off Form</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {/* Step 1: Select Record */}
        {step === 1 && (
          <div className="modal-body">
            <p className="modal-description">
              Select which record this form is for. You'll configure the table columns next.
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
                Next: Configure Columns
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Configure Columns */}
        {step === 2 && (
          <div className="modal-body">
            <div className="selected-record-banner">
              <span className="record-number">{selectedRecord.record_number}</span>
              <span className="record-name">{selectedRecord.name}</span>
              <button className="btn-link" onClick={() => setStep(1)}>Change</button>
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
                placeholder="Text shown at the top of the form..."
                rows={2}
              />
            </div>

            <div className="form-field">
              <label>Table Columns</label>
              <div className="columns-editor">
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
              <button className="btn-link" onClick={() => setStep(2)}>Edit columns</button>
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

            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setStep(2)}>Back</button>
              <button
                className="btn-primary"
                onClick={handleCreate}
                disabled={creating}
              >
                {creating ? 'Creating...' : 'Create Form Link'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
