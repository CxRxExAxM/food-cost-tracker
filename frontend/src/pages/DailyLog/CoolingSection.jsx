/**
 * Cooling Section (Record 5)
 *
 * Cooling log for food items.
 * - Add-entry pattern (no fixed rows)
 * - Tracks: item, start/end time, 2hr temp, 6hr temp, method
 * - Auto-flags if temps exceed thresholds (2hr > 70°F, 6hr > 41°F)
 */

import { useState } from 'react';
import {
  Snowflake, Plus, Trash2, AlertTriangle, Clock
} from 'lucide-react';
import api from '../../lib/axios';
import { useToast } from '../../contexts/ToastContext';

const COOLING_METHODS = [
  { id: 'ambient', label: 'Ambient' },
  { id: 'blast_chill', label: 'Blast Chill' },
  { id: 'ice_bath', label: 'Ice Bath' },
  { id: 'shallow_pan', label: 'Shallow Pan' },
  { id: 'other', label: 'Other' }
];

export default function CoolingSection({
  worksheet,
  outlet,
  records,
  setRecords,
  onSavingChange
}) {
  const [newItemName, setNewItemName] = useState('');
  const toast = useToast();

  const isLocked = worksheet?.status === 'approved';

  async function addRecord() {
    if (!worksheet || isLocked || !newItemName.trim()) return;

    try {
      onSavingChange(true);
      const response = await api.post(`/daily-log/worksheet/${worksheet.id}/cooling`, {
        item_name: newItemName.trim(),
        start_time: getCurrentTime()  // Pass local time instead of relying on server UTC
      });
      setRecords(prev => [...prev, response.data]);
      setNewItemName('');
    } catch (err) {
      console.error('Error adding cooling record:', err);
      toast.error(err.response?.data?.detail || 'Failed to add cooling record');
    } finally {
      onSavingChange(false);
    }
  }

  async function updateRecord(recordId, updates) {
    if (!worksheet || isLocked) return;

    try {
      onSavingChange(true);
      const response = await api.put(
        `/daily-log/worksheet/${worksheet.id}/cooling/${recordId}`,
        updates
      );
      setRecords(prev =>
        prev.map(r => r.id === recordId ? response.data : r)
      );
    } catch (err) {
      console.error('Error updating cooling record:', err);
      toast.error(err.response?.data?.detail || 'Failed to update');
    } finally {
      onSavingChange(false);
    }
  }

  async function deleteRecord(recordId) {
    if (!worksheet || isLocked) return;
    if (!confirm('Delete this cooling entry?')) return;

    try {
      onSavingChange(true);
      await api.delete(`/daily-log/worksheet/${worksheet.id}/cooling/${recordId}`);
      setRecords(prev => prev.filter(r => r.id !== recordId));
    } catch (err) {
      console.error('Error deleting cooling record:', err);
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

  return (
    <div className="cooling-section">
      <div className="section-header">
        <h2>
          <Snowflake size={20} />
          Cooling Log
        </h2>
        <span className="record-badge">Record 5</span>
      </div>

      <div className="section-info">
        <p>
          <strong>Thresholds:</strong> 2hr check ≤ 70°F | 6hr check ≤ 41°F
        </p>
      </div>

      {/* Add new entry */}
      {!isLocked && (
        <div className="add-entry-form">
          <input
            type="text"
            className="item-input"
            placeholder="Item being cooled..."
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

      {/* Cooling entries */}
      <div className="cooling-entries">
        {records.map(record => (
          <div
            key={record.id}
            className={`cooling-entry ${record.is_flagged ? 'flagged' : ''}`}
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

            <div className="cooling-grid">
              {/* Method */}
              <div className="field-group">
                <label>Method</label>
                <select
                  value={record.method || ''}
                  onChange={(e) => updateRecord(record.id, { method: e.target.value })}
                  disabled={isLocked}
                >
                  <option value="">Select...</option>
                  {COOLING_METHODS.map(m => (
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

              {/* 2hr Temp */}
              <div className="field-group">
                <label>2hr Temp</label>
                <div className="temp-input-wrapper">
                  <input
                    type="number"
                    step="0.1"
                    className={`temp-input-sm ${record.temp_2hr_f > 70 ? 'over-threshold' : ''}`}
                    placeholder="—"
                    value={record.temp_2hr_f ?? ''}
                    onChange={(e) => updateRecord(record.id, {
                      temp_2hr_f: e.target.value ? parseFloat(e.target.value) : null
                    })}
                    disabled={isLocked}
                  />
                  <span className="temp-unit">°F</span>
                </div>
              </div>

              {/* 6hr Temp */}
              <div className="field-group">
                <label>6hr Temp</label>
                <div className="temp-input-wrapper">
                  <input
                    type="number"
                    step="0.1"
                    className={`temp-input-sm ${record.temp_6hr_f > 41 ? 'over-threshold' : ''}`}
                    placeholder="—"
                    value={record.temp_6hr_f ?? ''}
                    onChange={(e) => updateRecord(record.id, {
                      temp_6hr_f: e.target.value ? parseFloat(e.target.value) : null
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
                <span>Temperature exceeds threshold - corrective action required</span>
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
          <Snowflake size={32} className="empty-icon" />
          <p>No cooling records today</p>
          <p className="empty-hint">Add an entry when you start cooling food</p>
        </div>
      )}
    </div>
  );
}
