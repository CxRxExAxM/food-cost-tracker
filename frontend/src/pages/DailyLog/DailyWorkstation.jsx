/**
 * Daily Workstation - The Daily Worksheet View
 *
 * Shows the daily monitoring worksheet for a specific outlet and date.
 * Kitchen staff can log temps, see flags, and sign their sections.
 * Tabbed interface shows only enabled sections per outlet config.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Thermometer, ChevronLeft, ChevronRight, Check, AlertTriangle,
  Calendar, RefreshCw, Flame, Snowflake, Wind, Home
} from 'lucide-react';
import api from '../../lib/axios';
import CoolerTempSection from './CoolerTempSection';
import CookReheatSection from './CookReheatSection';
import CoolingSection from './CoolingSection';
import ThawingSection from './ThawingSection';
import './DailyLog.css';

// Debounce delay for auto-save (ms)
const SAVE_DEBOUNCE_MS = 1500;

export default function DailyWorkstation() {
  const { outletName, dateStr } = useParams();
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

  // Pending changes queue for debounced saves
  const pendingChanges = useRef(new Map());
  const saveTimeoutRef = useRef(null);

  // Parse current date
  const currentDate = new Date(dateStr + 'T00:00:00');
  const isToday = dateStr === new Date().toISOString().split('T')[0];
  const isPast = currentDate < new Date(new Date().toISOString().split('T')[0] + 'T00:00:00');

  useEffect(() => {
    loadWorksheet();
  }, [outletName, dateStr]);

  async function loadWorksheet() {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/daily-log/worksheet/${encodeURIComponent(outletName)}/${dateStr}`);
      setWorksheet(response.data.worksheet);
      setOutlet(response.data.outlet);
      setCoolerReadings(response.data.cooler_readings || []);
      setCookingRecords(response.data.cooking_records || []);
      setCoolingRecords(response.data.cooling_records || []);
      setThawingRecords(response.data.thawing_records || []);

      // Set initial active tab based on what's enabled
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
        setError('Outlet not found');
      } else if (err.response?.status === 400) {
        setError(err.response.data?.detail || 'Invalid request');
      } else {
        setError('Failed to load worksheet. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  // Flush all pending changes to the server
  const flushPendingChanges = useCallback(async () => {
    if (!worksheet || pendingChanges.current.size === 0) return;

    setSaving(true);
    const changes = Array.from(pendingChanges.current.entries());
    pendingChanges.current.clear();

    try {
      // Process all pending changes
      for (const [key, { unitType, unitNumber, shift, updates }] of changes) {
        const response = await api.put(
          `/daily-log/worksheet/${worksheet.id}/coolers/${unitType}/${unitNumber}/${shift}`,
          updates
        );

        // Update local state with server response
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
  }, [worksheet]);

  // Debounced reading update - queues changes and saves after delay
  function handleReadingUpdate(unitType, unitNumber, shift, updates) {
    if (!worksheet) return;

    const key = `${unitType}-${unitNumber}-${shift}`;

    // Immediately update local state for responsive UI
    setCoolerReadings(prev =>
      prev.map(r =>
        r.unit_type === unitType && r.unit_number === unitNumber && r.shift === shift
          ? { ...r, ...updates }
          : r
      )
    );

    // Merge with any pending changes for this reading
    const existing = pendingChanges.current.get(key) || { unitType, unitNumber, shift, updates: {} };
    pendingChanges.current.set(key, {
      unitType,
      unitNumber,
      shift,
      updates: { ...existing.updates, ...updates }
    });

    // Clear existing timeout and set new one
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(flushPendingChanges, SAVE_DEBOUNCE_MS);
  }

  // Cleanup timeout on unmount
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
      await api.post(`/daily-log/worksheet/${worksheet.id}/coolers/sign`, {
        shift,
        recorded_by: recordedBy,
        signature_data: signatureData
      });

      // Reload to get updated signature state
      await loadWorksheet();
    } catch (err) {
      console.error('Error signing shift:', err);
    } finally {
      setSaving(false);
    }
  }

  function navigateDate(direction) {
    const date = new Date(dateStr + 'T00:00:00');
    date.setDate(date.getDate() + direction);
    const newDateStr = date.toISOString().split('T')[0];
    navigate(`/daily-log/${encodeURIComponent(outletName)}/${newDateStr}`);
  }

  function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    const options = { weekday: 'long', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
  }

  // Calculate which tabs are available
  const hasCoolerTab = outlet?.cooler_count > 0 || outlet?.freezer_count > 0;
  const hasCookingTab = outlet?.has_cooking;
  const hasCoolingTab = outlet?.has_cooling;
  const hasThawingTab = outlet?.has_thawing;

  // Build tabs array
  const tabs = [];
  if (hasCoolerTab) tabs.push({ id: 'cooler', label: 'Cooler Temps', icon: Thermometer });
  if (hasCookingTab) tabs.push({ id: 'cooking', label: 'Cook/Reheat', icon: Flame });
  if (hasCoolingTab) tabs.push({ id: 'cooling', label: 'Cooling', icon: Snowflake });
  if (hasThawingTab) tabs.push({ id: 'thawing', label: 'Thawing', icon: Wind });

  // Calculate completion stats for coolers
  const totalReadings = coolerReadings.length;
  const completedReadings = coolerReadings.filter(r => r.temperature_f !== null).length;
  const flaggedReadings = coolerReadings.filter(r => r.is_flagged).length;
  const amSigned = coolerReadings.some(r => r.shift === 'am' && r.signature_data);
  const pmSigned = coolerReadings.some(r => r.shift === 'pm' && r.signature_data);

  // Count flagged across all sections
  const totalFlagged = flaggedReadings +
    cookingRecords.filter(r => r.is_flagged).length +
    coolingRecords.filter(r => r.is_flagged).length +
    thawingRecords.filter(r => r.is_flagged).length;

  if (loading) {
    return (
      <div className="daily-workstation">
        <div className="loading-state">
          <RefreshCw size={24} className="loading-icon spinning" />
          <span>Loading worksheet...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="daily-workstation">
        <div className="workstation-header">
          <Link to="/daily-log" className="back-link">
            <ChevronLeft size={20} />
            <span>Back</span>
          </Link>
        </div>
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

  return (
    <div className="daily-workstation">
      {/* Header */}
      <div className="workstation-header">
        <div className="header-nav">
          <Link to="/" className="home-link" title="Dashboard">
            <Home size={18} />
          </Link>
          <Link to="/daily-log" className="back-link">
            <ChevronLeft size={20} />
            <span>Outlets</span>
          </Link>
          <Link to="/daily-log?view=calendar" className="calendar-link" title="Monthly Calendar">
            <Calendar size={16} />
            <span>Calendar</span>
          </Link>
        </div>

        <div className="outlet-info">
          <span className="outlet-badge">{outletName}</span>
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
            {formatDate(dateStr)}
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
        {/* Cooler/Freezer Section */}
        {activeTab === 'cooler' && hasCoolerTab && (
          <CoolerTempSection
            outlet={outlet}
            readings={coolerReadings}
            worksheetStatus={worksheet?.status}
            onReadingUpdate={handleReadingUpdate}
            onSignShift={handleSignShift}
          />
        )}

        {/* Cook/Reheat Section */}
        {activeTab === 'cooking' && hasCookingTab && (
          <CookReheatSection
            worksheet={worksheet}
            outlet={outlet}
            records={cookingRecords}
            setRecords={setCookingRecords}
            onSavingChange={setSaving}
          />
        )}

        {/* Cooling Section */}
        {activeTab === 'cooling' && hasCoolingTab && (
          <CoolingSection
            worksheet={worksheet}
            outlet={outlet}
            records={coolingRecords}
            setRecords={setCoolingRecords}
            onSavingChange={setSaving}
          />
        )}

        {/* Thawing Section */}
        {activeTab === 'thawing' && hasThawingTab && (
          <ThawingSection
            worksheet={worksheet}
            outlet={outlet}
            records={thawingRecords}
            setRecords={setThawingRecords}
            onSavingChange={setSaving}
          />
        )}
      </div>
    </div>
  );
}
