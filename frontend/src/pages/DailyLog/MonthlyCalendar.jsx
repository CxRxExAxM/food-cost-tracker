/**
 * Monthly Calendar View
 *
 * Shows completion status for daily log worksheets across a month.
 * - Visual indicators for complete, partial, flagged, empty days
 * - Click any day to navigate to that worksheet
 * - Summary stats at the top
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChevronLeft, ChevronRight, Check, AlertTriangle,
  Calendar, RefreshCw
} from 'lucide-react';
import api from '../../lib/axios';
import './MonthlyCalendar.css';

export default function MonthlyCalendar({ outlets, selectedOutlet, onOutletChange }) {
  const navigate = useNavigate();
  const [calendarData, setCalendarData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Current month/year being viewed
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth() + 1); // 1-indexed

  useEffect(() => {
    if (selectedOutlet) {
      loadCalendar();
    }
  }, [selectedOutlet, viewYear, viewMonth]);

  async function loadCalendar() {
    if (!selectedOutlet) return;

    try {
      setLoading(true);
      setError(null);
      const response = await api.get(
        `/daily-log/calendar/${encodeURIComponent(selectedOutlet.name)}/${viewYear}/${viewMonth}`
      );
      setCalendarData(response.data);
    } catch (err) {
      console.error('Error loading calendar:', err);
      setError('Failed to load calendar data');
    } finally {
      setLoading(false);
    }
  }

  function navigateMonth(direction) {
    let newMonth = viewMonth + direction;
    let newYear = viewYear;

    if (newMonth < 1) {
      newMonth = 12;
      newYear--;
    } else if (newMonth > 12) {
      newMonth = 1;
      newYear++;
    }

    setViewMonth(newMonth);
    setViewYear(newYear);
  }

  function goToToday() {
    setViewYear(today.getFullYear());
    setViewMonth(today.getMonth() + 1);
  }

  function handleDayClick(day) {
    if (day.is_future || !selectedOutlet) return;

    // Navigate to the worksheet for this day
    navigate(`/daily-log/${encodeURIComponent(selectedOutlet.name)}/${day.date}`);
  }

  function getStatusClass(status) {
    switch (status) {
      case 'complete': return 'status-complete';
      case 'flagged': return 'status-flagged';
      case 'partial': return 'status-partial';
      case 'future': return 'status-future';
      default: return 'status-empty';
    }
  }

  function getStatusIcon(status) {
    switch (status) {
      case 'complete':
        return <Check size={14} className="status-icon complete" />;
      case 'flagged':
        return <AlertTriangle size={14} className="status-icon flagged" />;
      case 'partial':
        return <div className="status-icon partial-dot" />;
      default:
        return null;
    }
  }

  // Check if we're viewing the current month
  const isCurrentMonth = viewYear === today.getFullYear() && viewMonth === today.getMonth() + 1;

  // Get day names for header
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  // Build calendar grid with padding for first week
  function buildCalendarGrid() {
    if (!calendarData?.days) return [];

    const days = calendarData.days;
    const firstDay = new Date(viewYear, viewMonth - 1, 1).getDay(); // 0 = Sunday

    // Pad the beginning with empty cells
    const grid = [];
    for (let i = 0; i < firstDay; i++) {
      grid.push({ empty: true, key: `empty-${i}` });
    }

    // Add actual days
    days.forEach(day => {
      grid.push({ ...day, key: day.date });
    });

    return grid;
  }

  const calendarGrid = buildCalendarGrid();

  return (
    <div className="monthly-calendar">
      {/* Outlet Selector */}
      <div className="calendar-controls">
        <div className="outlet-selector">
          <label>Outlet:</label>
          <select
            value={selectedOutlet?.name || ''}
            onChange={(e) => {
              const outlet = outlets.find(o => o.name === e.target.value);
              onOutletChange(outlet);
            }}
          >
            {outlets.map(outlet => (
              <option key={outlet.id} value={outlet.name}>
                {outlet.name} - {outlet.full_name}
              </option>
            ))}
          </select>
        </div>

        {/* Month Navigation */}
        <div className="month-navigation">
          <button
            className="nav-btn"
            onClick={() => navigateMonth(-1)}
            title="Previous month"
          >
            <ChevronLeft size={20} />
          </button>

          <div className="current-month">
            <Calendar size={16} />
            <span>{calendarData?.month_name || ''} {viewYear}</span>
          </div>

          <button
            className="nav-btn"
            onClick={() => navigateMonth(1)}
            title="Next month"
          >
            <ChevronRight size={20} />
          </button>

          {!isCurrentMonth && (
            <button
              className="today-btn"
              onClick={goToToday}
            >
              Today
            </button>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      {calendarData?.summary && (
        <div className="calendar-summary">
          <div className="summary-stat">
            <span className="stat-value complete">{calendarData.summary.complete}</span>
            <span className="stat-label">Complete</span>
          </div>
          <div className="summary-stat">
            <span className="stat-value flagged">{calendarData.summary.flagged}</span>
            <span className="stat-label">Flagged</span>
          </div>
          <div className="summary-stat">
            <span className="stat-value partial">{calendarData.summary.partial}</span>
            <span className="stat-label">Partial</span>
          </div>
          <div className="summary-stat">
            <span className="stat-value empty">{calendarData.summary.empty}</span>
            <span className="stat-label">Missing</span>
          </div>
          <div className="summary-stat completion-rate">
            <span className="stat-value">{calendarData.summary.completion_rate}%</span>
            <span className="stat-label">Completion</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="calendar-loading">
          <RefreshCw size={24} className="spinning" />
          <span>Loading...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="calendar-error">
          <AlertTriangle size={20} />
          <span>{error}</span>
          <button onClick={loadCalendar}>Retry</button>
        </div>
      )}

      {/* Calendar Grid */}
      {!loading && !error && calendarData && (
        <div className="calendar-grid">
          {/* Day Headers */}
          <div className="calendar-header">
            {dayNames.map(day => (
              <div key={day} className="day-header">{day}</div>
            ))}
          </div>

          {/* Day Cells */}
          <div className="calendar-days">
            {calendarGrid.map(day => (
              day.empty ? (
                <div key={day.key} className="day-cell empty-cell" />
              ) : (
                <div
                  key={day.key}
                  className={`day-cell ${getStatusClass(day.status)} ${day.is_today ? 'is-today' : ''} ${day.is_future ? 'is-future' : 'clickable'}`}
                  onClick={() => handleDayClick(day)}
                  title={day.is_future ? 'Future date' : `${day.status} - Click to view`}
                >
                  <span className="day-number">{day.day}</span>
                  {getStatusIcon(day.status)}
                  {day.sigs_present !== undefined && day.sigs_required > 0 && (
                    <span className="sig-count">
                      {day.sigs_present}/{day.sigs_required}
                    </span>
                  )}
                </div>
              )
            ))}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="calendar-legend">
        <div className="legend-item">
          <div className="legend-swatch complete" />
          <span>Complete</span>
        </div>
        <div className="legend-item">
          <div className="legend-swatch flagged" />
          <span>Flagged</span>
        </div>
        <div className="legend-item">
          <div className="legend-swatch partial" />
          <span>Partial</span>
        </div>
        <div className="legend-item">
          <div className="legend-swatch empty" />
          <span>Not started</span>
        </div>
      </div>
    </div>
  );
}
