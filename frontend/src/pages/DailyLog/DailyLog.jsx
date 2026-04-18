/**
 * Daily Log Module - Main Entry Point
 *
 * Two views:
 * 1. Outlet selector - Kitchen staff scan QR → select outlet → view today's worksheet
 * 2. Monthly calendar - Management view showing completion status across the month
 */

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Thermometer, ChevronRight, Calendar, Home, List } from 'lucide-react';
import api from '../../lib/axios';
import MonthlyCalendar from './MonthlyCalendar';
import './DailyLog.css';

export default function DailyLog() {
  const navigate = useNavigate();
  const [outlets, setOutlets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState('outlets'); // 'outlets' or 'calendar'
  const [selectedOutlet, setSelectedOutlet] = useState(null);

  // Check for remembered outlet
  const rememberedOutlet = localStorage.getItem('dailyLogOutlet');

  useEffect(() => {
    loadOutlets();
  }, []);

  // Auto-navigate if outlet is remembered (only for outlet view)
  useEffect(() => {
    if (rememberedOutlet && outlets.length > 0 && view === 'outlets') {
      const outlet = outlets.find(o => o.name === rememberedOutlet);
      if (outlet) {
        navigateToWorkstation(rememberedOutlet);
      } else {
        // Outlet no longer valid, clear it
        localStorage.removeItem('dailyLogOutlet');
      }
    }
  }, [rememberedOutlet, outlets, view]);

  // Set default selected outlet for calendar view
  useEffect(() => {
    if (outlets.length > 0 && !selectedOutlet) {
      setSelectedOutlet(outlets[0]);
    }
  }, [outlets]);

  async function loadOutlets() {
    try {
      setLoading(true);
      const response = await api.get('/daily-log/outlets');
      setOutlets(response.data.data || []);
    } catch (err) {
      setError('Failed to load outlets. Please try again.');
      console.error('Error loading outlets:', err);
    } finally {
      setLoading(false);
    }
  }

  function navigateToWorkstation(outletName) {
    const today = new Date().toISOString().split('T')[0];
    navigate(`/daily-log/${encodeURIComponent(outletName)}/${today}`);
  }

  function handleOutletSelect(outlet) {
    // Remember this outlet for next time
    localStorage.setItem('dailyLogOutlet', outlet.name);
    navigateToWorkstation(outlet.name);
  }

  function getOutletSummary(outlet) {
    const parts = [];
    if (outlet.cooler_count > 0) {
      parts.push(`${outlet.cooler_count} cooler${outlet.cooler_count > 1 ? 's' : ''}`);
    }
    if (outlet.freezer_count > 0) {
      parts.push(`${outlet.freezer_count} freezer${outlet.freezer_count > 1 ? 's' : ''}`);
    }
    return parts.join(', ') || 'No equipment configured';
  }

  if (loading) {
    return (
      <div className="daily-log-page">
        <div className="loading-state">
          <Thermometer size={32} className="loading-icon" />
          <span>Loading outlets...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="daily-log-page">
        <div className="error-state">
          <p>{error}</p>
          <button className="btn-primary" onClick={loadOutlets}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (outlets.length === 0) {
    return (
      <div className="daily-log-page">
        <div className="empty-state">
          <Thermometer size={48} className="empty-icon" />
          <h2>No Outlets Configured</h2>
          <p>
            Daily monitoring is not enabled for any outlets.
            Configure outlets in EHC Settings to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="daily-log-page">
      <div className="daily-log-topbar">
        <Link to="/" className="back-to-dashboard">
          <Home size={18} />
          <span>Dashboard</span>
        </Link>

        {/* View Toggle */}
        <div className="view-toggle">
          <button
            className={`toggle-btn ${view === 'outlets' ? 'active' : ''}`}
            onClick={() => setView('outlets')}
          >
            <List size={16} />
            <span>Outlets</span>
          </button>
          <button
            className={`toggle-btn ${view === 'calendar' ? 'active' : ''}`}
            onClick={() => setView('calendar')}
          >
            <Calendar size={16} />
            <span>Calendar</span>
          </button>
        </div>
      </div>

      {view === 'outlets' ? (
        <>
          <div className="daily-log-header">
            <div className="header-icon">
              <Thermometer size={32} />
            </div>
            <div className="header-text">
              <h1>Daily Logs</h1>
              <p>Select your outlet to start logging</p>
            </div>
          </div>

          <div className="outlet-selector">
            {outlets.map(outlet => (
              <button
                key={outlet.id}
                className="outlet-card"
                onClick={() => handleOutletSelect(outlet)}
              >
                <div className="outlet-card-content">
                  <div className="outlet-name">{outlet.full_name || outlet.name}</div>
                  <div className="outlet-tag">{outlet.name}</div>
                  <div className="outlet-summary">{getOutletSummary(outlet)}</div>
                </div>
                <ChevronRight size={24} className="outlet-arrow" />
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="daily-log-header">
            <div className="header-icon">
              <Calendar size={32} />
            </div>
            <div className="header-text">
              <h1>Monthly Calendar</h1>
              <p>Track completion status across the month</p>
            </div>
          </div>

          <MonthlyCalendar
            outlets={outlets}
            selectedOutlet={selectedOutlet}
            onOutletChange={setSelectedOutlet}
          />
        </>
      )}
    </div>
  );
}
