/**
 * Simple Sign-off Form Creation Modal
 *
 * For generic PDF acknowledgment forms:
 * 1. Admin uploads a PDF document
 * 2. Admin sets expected signature count
 * 3. Staff view the PDF and sign to acknowledge
 */

import { useState, useEffect } from 'react';
import { API_BASE, fetchWithAuth } from '../tabs/shared';

export default function SimpleSignoffModal({
  isOpen,
  onClose,
  activeCycle,
  records,
  onFormCreated,
  toast
}) {
  const [step, setStep] = useState(1); // 1: Select record, 2: Upload & configure
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [title, setTitle] = useState('');
  const [expectedResponses, setExpectedResponses] = useState('');
  const [uploadedDoc, setUploadedDoc] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setSelectedRecord(null);
      setTitle('');
      setExpectedResponses('');
      setUploadedDoc(null);
    }
  }, [isOpen]);

  async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast?.error?.('Only PDF files are allowed');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast?.error?.('File too large (max 10MB)');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/ehc/form-links/upload-document`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploadedDoc(data);
      toast?.success?.('Document uploaded');
    } catch (error) {
      toast?.error?.(error.message || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  }

  async function handleCreate() {
    if (!selectedRecord || !uploadedDoc) {
      toast?.error?.('Please select a record and upload a document');
      return;
    }

    try {
      setCreating(true);

      const config = {
        document_path: uploadedDoc.document_path,
        document_name: uploadedDoc.document_name,
        property_name: 'Fairmont Scottsdale Princess' // TODO: Get from org settings
      };

      const payload = {
        form_type: 'simple_signoff',
        record_id: selectedRecord.id,
        title: title || `${selectedRecord.name} - EHC ${activeCycle.year}`,
        config,
        expected_responses: expectedResponses ? parseInt(expectedResponses) : null
      };

      const data = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/form-links`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      toast?.success?.('Form link created');
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
      <div className="modal-content form-create-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Simple Sign-off Form</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {step === 1 && (
          <div className="modal-body">
            <p className="modal-description">
              Select which record this form is for. Staff will view a PDF document
              and sign to acknowledge they've read it.
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
                Next
              </button>
            </div>
          </div>
        )}

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
              <label>Expected Signatures (optional)</label>
              <input
                type="number"
                value={expectedResponses}
                onChange={e => setExpectedResponses(e.target.value)}
                placeholder="e.g., 50"
                min="1"
              />
              <span className="field-hint">Leave blank if unknown</span>
            </div>

            <div className="form-field">
              <label>PDF Document *</label>
              {!uploadedDoc ? (
                <div className="file-upload-area">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    disabled={uploading}
                    id="doc-upload"
                  />
                  <label htmlFor="doc-upload" className="file-upload-label">
                    {uploading ? 'Uploading...' : 'Click or drag to upload PDF'}
                  </label>
                </div>
              ) : (
                <div className="uploaded-file">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{uploadedDoc.document_name}</span>
                  <span className="file-size">
                    ({Math.round(uploadedDoc.file_size / 1024)} KB)
                  </span>
                  <button
                    className="btn-link danger"
                    onClick={() => setUploadedDoc(null)}
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>

            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setStep(1)}>Back</button>
              <button
                className="btn-primary"
                onClick={handleCreate}
                disabled={creating || !uploadedDoc}
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
