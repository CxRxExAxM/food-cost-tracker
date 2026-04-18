/**
 * Daily Log Module - Main Entry Point
 *
 * Outlet selector for daily monitoring workstation.
 * Kitchen staff scan QR → select outlet → view today's worksheet.
 */

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Thermometer, ChevronRight, Calendar, Home } from 'lucide-react';
import api from '../../lib/axios';
import './DailyLog.css';

export default function DailyLog() {
  const navigate = useNavigate();
  const [outlets, setOutlets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for remembered outlet
  const rememberedOutlet = localStorage.getItem('dailyLogOutlet');

  useEffect(() => {
    loadOutlets();
  }, []);

  // Auto-navigate if outlet is remembered
  useEffect(() => {
    if (rememberedOutlet && outlets.length > 0) {
      const outletExists = outlets.some(o => o.name === rememberedOutlet);
      if (outletExists) {
        navigateToWorkstation(rememberedOutlet);
      } else {
        // Outlet no longer valid, clear it
        localStorage.removeItem('dailyLogOutlet');
      }
    }
  }, [rememberedOutlet, outlets]);

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
      </div>

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

      <div className="daily-log-footer">
        <button
          className="btn-secondary"
          onClick={() => {
            localStorage.removeItem('dailyLogOutlet');
            // Could navigate to calendar view here
          }}
        >
          <Calendar size={16} />
          View Calendar
        </button>
      </div>
    </div>
  );
}
