/**
 * Public Daily Workstation - Token-based Access
 *
 * Same functionality as DailyWorkstation but accessed via QR code token.
 * No authentication required - uses public API endpoints.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Thermometer, ChevronLeft, ChevronRight, Check, AlertTriangle,
  Calendar, RefreshCw, Flame, Snowflake, Wind
} from 'lucide-react';
import api from '../../lib/axios';
import CoolerTempSection from './CoolerTempSection';
import CookReheatSection from './CookReheatSection';
import CoolingSection from './CoolingSection';
import ThawingSection from './ThawingSection';
import './DailyLog.css';

const SAVE_DEBOUNCE_MS = 1500;

export default function PublicDailyWorkstation() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [worksheet, setWorksheet] = useState(null);
  const [outlet, setOutlet] = useState(null);
  const [coolerReadings, setCoolerReadings] = useState([]);
  const [cookingRecords, setCookingRecords] = useState([]);
  const [coolingRecords, setCoolingRecords] = useState([]);
  const [thawingRecords, setThawingRecords] = useState([]);
  const [activeTab, setActiveTab] = useState('cooler');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [currentDate, setCurrentDate] = useState(new Date().toISOString().split('T')[0]);

  const pendingChanges = useRef(new Map());
  const saveTimeoutRef = useRef(null);

  const isToday = currentDate === new Date().toISOString().split('T')[0];

  useEffect(() => {
    loadWorksheet();
  }, [token, currentDate]);

  async function loadWorksheet() {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/daily-log/public/${token}/${currentDate}`);
      setWorksheet(response.data.worksheet);
      setOutlet(response.data.outlet);
      setCoolerReadings(response.data.cooler_readings || []);
      setCookingRecords(response.data.cooking_records || []);
      setCoolingRecords(response.data.cooling_records || []);
      setThawingRecords(response.data.thawing_records || []);

      // Set initial active tab
      const o = response.data.outlet;
      if (o?.cooler_count > 0 || o?.freezer_count > 0) {
        setActiveTab('cooler');
      } else if (o?.has_cooking) {
        setActiveTab('cooking');
      } else if (o?.has_cooling) {
        setActiveTab('cooling');
      } else if (o?.has_thawing) {
        setActiveTab('thawing');
      }
    } catch (err) {
      console.error('Error loading worksheet:', err);
      if (err.response?.status === 404) {
        setError('Invalid or expired access link');
      } else {
        setError('Failed to load worksheet. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  const flushPendingChanges = useCallback(async () => {
    if (!worksheet || pendingChanges.current.size === 0) return;

    setSaving(true);
    const changes = Array.from(pendingChanges.current.entries());
    pendingChanges.current.clear();

    try {
      for (const [key, { unitType, unitNumber, shift, updates }] of changes) {
        const response = await api.put(
          `/daily-log/public/${token}/coolers/${unitType}/${unitNumber}/${shift}`,
          updates
        );
        setCoolerReadings(prev =>
          prev.map(r =>
            r.unit_type === unitType && r.unit_number === unitNumber && r.shift === shift
              ? response.data
              : r
          )
        );
      }
    } catch (err) {
      console.error('Error updating readings:', err);
    } finally {
      setSaving(false);
    }
  }, [worksheet, token]);

  function handleReadingUpdate(unitType, unitNumber, shift, updates) {
    if (!worksheet) return;

    const key = `${unitType}-${unitNumber}-${shift}`;

    setCoolerReadings(prev =>
      prev.map(r =>
        r.unit_type === unitType && r.unit_number === unitNumber && r.shift === shift
          ? { ...r, ...updates }
          : r
      )
    );

    const existing = pendingChanges.current.get(key) || { unitType, unitNumber, shift, updates: {} };
    pendingChanges.current.set(key, {
      unitType,
      unitNumber,
      shift,
      updates: { ...existing.updates, ...updates }
    });

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(flushPendingChanges, SAVE_DEBOUNCE_MS);
  }

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  async function handleSignShift(shift, recordedBy, signatureData) {
    if (!worksheet) return;

    try {
      setSaving(true);
      await api.post(`/daily-log/public/${token}/coolers/sign`, {
        shift,
        recorded_by: recordedBy,
        signature_data: signatureData
      });
      await loadWorksheet();
    } catch (err) {
      console.error('Error signing shift:', err);
    } finally {
      setSaving(false);
    }
  }

  function navigateDate(direction) {
    const date = new Date(currentDate + 'T00:00:00');
    date.setDate(date.getDate() + direction);
    setCurrentDate(date.toISOString().split('T')[0]);
  }

  function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    const options = { weekday: 'long', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
  }

  const hasCoolerTab = outlet?.cooler_count > 0 || outlet?.freezer_count > 0;
  const hasCookingTab = outlet?.has_cooking;
  const hasCoolingTab = outlet?.has_cooling;
  const hasThawingTab = outlet?.has_thawing;

  const tabs = [];
  if (hasCoolerTab) tabs.push({ id: 'cooler', label: 'Cooler Temps', icon: Thermometer });
  if (hasCookingTab) tabs.push({ id: 'cooking', label: 'Cook/Reheat', icon: Flame });
  if (hasCoolingTab) tabs.push({ id: 'cooling', label: 'Cooling', icon: Snowflake });
  if (hasThawingTab) tabs.push({ id: 'thawing', label: 'Thawing', icon: Wind });

  const totalReadings = coolerReadings.length;
  const completedReadings = coolerReadings.filter(r => r.temperature_f !== null).length;
  const flaggedReadings = coolerReadings.filter(r => r.is_flagged).length;
  const amSigned = coolerReadings.some(r => r.shift === 'am' && r.signature_data);
  const pmSigned = coolerReadings.some(r => r.shift === 'pm' && r.signature_data);

  const totalFlagged = flaggedReadings +
    cookingRecords.filter(r => r.is_flagged).length +
    coolingRecords.filter(r => r.is_flagged).length +
    thawingRecords.filter(r => r.is_flagged).length;

  if (loading) {
    return (
      <div className="daily-workstation public-workstation">
        <div className="loading-state">
          <RefreshCw size={24} className="loading-icon spinning" />
          <span>Loading worksheet...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="daily-workstation public-workstation">
        <div className="error-state">
          <AlertTriangle size={32} />
          <p>{error}</p>
          <button className="btn-primary" onClick={loadWorksheet}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Create a modified worksheet object that uses public API paths
  const publicWorksheet = {
    ...worksheet,
    // Flag to indicate this is public access
    _publicToken: token
  };

  return (
    <div className="daily-workstation public-workstation">
      {/* Header */}
      <div className="workstation-header">
        <div className="outlet-info">
          <span className="outlet-badge">{outlet?.name}</span>
          <span className="outlet-full-name">{outlet?.full_name}</span>
        </div>
      </div>

      {/* Date Navigation */}
      <div className="date-navigation">
        <button
          className="date-nav-btn"
          onClick={() => navigateDate(-1)}
          title="Previous day"
        >
          <ChevronLeft size={20} />
        </button>

        <div className="current-date">
          <Calendar size={16} />
          <span className={isToday ? 'today' : ''}>
            {formatDate(currentDate)}
            {isToday && <span className="today-badge">Today</span>}
          </span>
        </div>

        <button
          className="date-nav-btn"
          onClick={() => navigateDate(1)}
          disabled={isToday}
          title="Next day"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <div className="status-item">
          <span className="status-label">Status</span>
          <span className={`status-value ${worksheet?.status}`}>
            {worksheet?.status === 'approved' && <Check size={14} />}
            {worksheet?.status || 'open'}
          </span>
        </div>

        <div className="status-item">
          <span className="status-label">Readings</span>
          <span className="status-value">
            {completedReadings} / {totalReadings}
          </span>
        </div>

        {totalFlagged > 0 && (
          <div className="status-item flagged">
            <AlertTriangle size={14} />
            <span>{totalFlagged} flagged</span>
          </div>
        )}

        <div className="status-item">
          <span className="status-label">Signed</span>
          <span className="status-value">
            <span className={amSigned ? 'signed' : 'unsigned'}>AM</span>
            {' / '}
            <span className={pmSigned ? 'signed' : 'unsigned'}>PM</span>
          </span>
        </div>
      </div>

      {/* Saving Indicator */}
      {saving && (
        <div className="saving-indicator">
          <RefreshCw size={14} className="spinning" />
          <span>Saving...</span>
        </div>
      )}

      {/* Tab Navigation */}
      {tabs.length > 1 && (
        <div className="worksheet-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`worksheet-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={16} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Worksheet Content */}
      <div className="worksheet-content">
        {activeTab === 'cooler' && hasCoolerTab && (
          <CoolerTempSection
            outlet={outlet}
            readings={coolerReadings}
            worksheetStatus={worksheet?.status}
            onReadingUpdate={handleReadingUpdate}
            onSignShift={handleSignShift}
          />
        )}

        {activeTab === 'cooking' && hasCookingTab && (
          <CookReheatSection
            worksheet={publicWorksheet}
            outlet={outlet}
            records={cookingRecords}
            setRecords={setCookingRecords}
            onSavingChange={setSaving}
            publicToken={token}
          />
        )}

        {activeTab === 'cooling' && hasCoolingTab && (
          <CoolingSection
            worksheet={publicWorksheet}
            outlet={outlet}
            records={coolingRecords}
            setRecords={setCoolingRecords}
            onSavingChange={setSaving}
            publicToken={token}
          />
        )}

        {activeTab === 'thawing' && hasThawingTab && (
          <ThawingSection
            worksheet={publicWorksheet}
            outlet={outlet}
            records={thawingRecords}
            setRecords={setThawingRecords}
            onSavingChange={setSaving}
            publicToken={token}
          />
        )}
      </div>
    </div>
  );
}
