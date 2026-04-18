/**
 * Thawing Section (Record 12)
 *
 * Thawing log for food items.
 * - Add-entry pattern (no fixed rows)
 * - Tracks: item, start time, finish date/time, finish temp, method
 * - Auto-flags if finish temp > 41°F
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Wind, Plus, Trash2, AlertTriangle, Clock
} from 'lucide-react';
import api from '../../lib/axios';
import { useToast } from '../../contexts/ToastContext';

const SAVE_DEBOUNCE_MS = 1500;

const THAWING_METHODS = [
  { id: 'walkin', label: 'Walk-in Cooler' },
  { id: 'running_water', label: 'Running Water' },
  { id: 'microwave', label: 'Microwave' },
  { id: 'cooking', label: 'During Cooking' },
  { id: 'other', label: 'Other' }
];

export default function ThawingSection({
  worksheet,
  outlet,
  records,
  setRecords,
  onSavingChange,
  publicToken  // Token for public (QR code) access - uses public API endpoints
}) {
  // Build API base path - uses public endpoint when accessed via QR code
  const apiBase = publicToken
    ? `/daily-log/public/${publicToken}`
    : `/daily-log/worksheet/${worksheet?.id}`;

  const [newItemName, setNewItemName] = useState('');
  const toast = useToast();

  // Debounce state for auto-save
  const pendingChanges = useRef(new Map());
  const saveTimeoutRef = useRef(null);

  const isLocked = worksheet?.status === 'approved';

  async function addRecord() {
    if ((!worksheet && !publicToken) || isLocked || !newItemName.trim()) return;

    try {
      onSavingChange(true);
      const response = await api.post(`${apiBase}/thawing`, {
        item_name: newItemName.trim(),
        start_time: getCurrentTime()  // Pass local time instead of relying on server UTC
      });
      setRecords(prev => [...prev, response.data]);
      setNewItemName('');
    } catch (err) {
      console.error('Error adding thawing record:', err);
      toast.error(err.response?.data?.detail || 'Failed to add thawing record');
    } finally {
      onSavingChange(false);
    }
  }

  // Flush pending changes to server
  const flushPendingChanges = useCallback(async () => {
    if ((!worksheet && !publicToken) || pendingChanges.current.size === 0) return;

    onSavingChange(true);
    const changes = Array.from(pendingChanges.current.entries());
    pendingChanges.current.clear();

    try {
      for (const [recordId, updates] of changes) {
        const response = await api.put(
          `${apiBase}/thawing/${recordId}`,
          updates
        );
        setRecords(prev =>
          prev.map(r => r.id === recordId ? response.data : r)
        );
      }
    } catch (err) {
      console.error('Error updating thawing record:', err);
      toast.error(err.response?.data?.detail || 'Failed to update');
    } finally {
      onSavingChange(false);
    }
  }, [worksheet, publicToken, apiBase, setRecords, onSavingChange, toast]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  function updateRecord(recordId, updates) {
    if ((!worksheet && !publicToken) || isLocked) return;

    // Immediately update local state for responsive UI
    setRecords(prev =>
      prev.map(r => r.id === recordId ? { ...r, ...updates } : r)
    );

    // Merge with any pending changes for this record
    const existing = pendingChanges.current.get(recordId) || {};
    pendingChanges.current.set(recordId, { ...existing, ...updates });

    // Clear existing timeout and set new one
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(flushPendingChanges, SAVE_DEBOUNCE_MS);
  }

  async function deleteRecord(recordId) {
    if ((!worksheet && !publicToken) || isLocked) return;
    if (!confirm('Delete this thawing entry?')) return;

    try {
      onSavingChange(true);
      await api.delete(`${apiBase}/thawing/${recordId}`);
      setRecords(prev => prev.filter(r => r.id !== recordId));
    } catch (err) {
      console.error('Error deleting thawing record:', err);
      toast.error(err.response?.data?.detail || 'Failed to delete');
    } finally {
      onSavingChange(false);
    }
  }

  function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  function formatTimeForInput(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  }

  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  return (
    <div className="thawing-section">
      <div className="section-header">
        <h2>
          <Wind size={20} />
          Thawing Log
        </h2>
        <span className="record-badge">Record 12</span>
      </div>

      <div className="section-info">
        <p>
          <strong>Threshold:</strong> Finish temp ≤ 41°F
        </p>
      </div>

      {/* Add new entry */}
      {!isLocked && (
        <div className="add-entry-form">
          <input
            type="text"
            className="item-input"
            placeholder="Item being thawed..."
            value={newItemName}
            onChange={(e) => setNewItemName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addRecord()}
          />
          <button
            className="btn-primary"
            onClick={addRecord}
            disabled={!newItemName.trim()}
          >
            <Plus size={16} />
            Add
          </button>
        </div>
      )}

      {/* Thawing entries */}
      <div className="thawing-entries">
        {records.map(record => (
          <div
            key={record.id}
            className={`thawing-entry ${record.is_flagged ? 'flagged' : ''}`}
          >
            <div className="entry-header">
              <span className="item-name">{record.item_name}</span>
              {!isLocked && (
                <button
                  className="delete-btn"
                  onClick={() => deleteRecord(record.id)}
                  title="Delete entry"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>

            <div className="thawing-grid">
              {/* Method */}
              <div className="field-group">
                <label>Method</label>
                <select
                  value={record.method || ''}
                  onChange={(e) => updateRecord(record.id, { method: e.target.value })}
                  disabled={isLocked}
                >
                  <option value="">Select...</option>
                  {THAWING_METHODS.map(m => (
                    <option key={m.id} value={m.id}>{m.label}</option>
                  ))}
                </select>
              </div>

              {/* Start Time */}
              <div className="field-group">
                <label>Started</label>
                <input
                  type="time"
                  className="time-input"
                  value={record.start_time ? formatTimeForInput(record.start_time) : getCurrentTime()}
                  onChange={(e) => updateRecord(record.id, { start_time: e.target.value })}
                  disabled={isLocked}
                />
              </div>

              {/* Finish Date */}
              <div className="field-group">
                <label>Finish Date</label>
                <input
                  type="date"
                  value={record.finish_date || ''}
                  onChange={(e) => updateRecord(record.id, { finish_date: e.target.value })}
                  disabled={isLocked}
                />
              </div>

              {/* Finish Time */}
              <div className="field-group">
                <label>Finish Time</label>
                <input
                  type="time"
                  value={record.finish_time || ''}
                  onChange={(e) => updateRecord(record.id, { finish_time: e.target.value })}
                  disabled={isLocked}
                />
              </div>

              {/* Finish Temp */}
              <div className="field-group">
                <label>Finish Temp</label>
                <div className="temp-input-wrapper">
                  <input
                    type="number"
                    step="0.1"
                    className={`temp-input-sm ${record.finish_temp_f > 41 ? 'over-threshold' : ''}`}
                    placeholder="—"
                    value={record.finish_temp_f ?? ''}
                    onChange={(e) => updateRecord(record.id, {
                      finish_temp_f: e.target.value ? parseFloat(e.target.value) : null
                    })}
                    disabled={isLocked}
                  />
                  <span className="temp-unit">°F</span>
                </div>
              </div>
            </div>

            {record.is_flagged && (
              <div className="flagged-row">
                <AlertTriangle size={14} />
                <span>Finish temp exceeds 41°F - corrective action required</span>
              </div>
            )}

            {record.is_flagged && (
              <textarea
                className="corrective-textarea"
                placeholder="Describe corrective action taken..."
                value={record.corrective_action || ''}
                onChange={(e) => updateRecord(record.id, { corrective_action: e.target.value })}
                disabled={isLocked}
              />
            )}
          </div>
        ))}
      </div>

      {records.length === 0 && (
        <div className="empty-section">
          <Wind size={32} className="empty-icon" />
          <p>No thawing records today</p>
          <p className="empty-hint">Add an entry when you start thawing food</p>
        </div>
      )}
    </div>
  );
}
