import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import Navigation from '../../components/Navigation';
import MonthDetailModal from './MonthDetailModal';
import axios from '../../lib/axios';
import './Waste.css';

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function Waste() {
  const { user } = useAuth();
  const currentYear = new Date().getFullYear();

  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [goal, setGoal] = useState(null);
  const [summary, setSummary] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingGoal, setEditingGoal] = useState(false);
  const [goalInput, setGoalInput] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(null);

  useEffect(() => {
    fetchData();
  }, [selectedYear]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch goal, summary, and metrics in parallel
      const [goalRes, summaryRes, metricsRes] = await Promise.all([
        axios.get(`/api/waste/goals?year=${selectedYear}`),
        axios.get(`/api/waste/summary?year=${selectedYear}`),
        axios.get(`/api/waste/metrics?year=${selectedYear}`)
      ]);

      console.log('Goal response:', goalRes.data);
      console.log('Summary response:', summaryRes.data);
      console.log('Metrics response:', metricsRes.data);

      setGoal(goalRes.data);
      setGoalInput(goalRes.data.target_grams_per_cover);
      setSummary(summaryRes.data);
      setMetrics(Array.isArray(metricsRes.data) ? metricsRes.data : []);
    } catch (error) {
      console.error('Error fetching waste data:', error);
      console.error('Error details:', error.response?.data);
      // Set safe defaults on error
      setGoal({ target_grams_per_cover: 0 });
      setGoalInput(0);
      setSummary({ ytd_actual_grams_per_cover: 0, variance: 0, variance_pct: 0, total_diversion_grams: 0, total_covers: 0 });
      setMetrics([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGoalEdit = () => {
    setEditingGoal(true);
  };

  const handleGoalSave = async () => {
    try {
      const target = parseFloat(goalInput);
      if (isNaN(target) || target < 0) {
        alert('Please enter a valid non-negative number');
        return;
      }

      await axios.put('/api/waste/goals', null, {
        params: {
          year: selectedYear,
          target_grams_per_cover: target
        }
      });

      setEditingGoal(false);
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Error saving goal:', error);
      alert('Failed to save goal');
    }
  };

  const handleGoalCancel = () => {
    setGoalInput(goal.target_grams_per_cover);
    setEditingGoal(false);
  };

  const handleMonthClick = (metric) => {
    setSelectedMonth(metric);
  };

  const handleMonthClose = () => {
    setSelectedMonth(null);
    fetchData(); // Refresh data after modal closes
  };

  const getVarianceColor = (value) => {
    if (!value || value === 0) return '';
    return value < 0 ? 'variance-positive' : 'variance-negative';
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return '—';
    return typeof value === 'number' ? value.toLocaleString() : value;
  };

  const formatDecimal = (value, decimals = 2) => {
    if (value === null || value === undefined) return '—';
    return typeof value === 'number' ? value.toFixed(decimals) : value;
  };

  if (loading) {
    return (
      <div className="waste-page">
        <Navigation />
        <div className="waste-container">
          <div className="loading">Loading waste tracking data...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="waste-page">
      <Navigation />
      <div className="waste-container">
        {/* Header */}
        <header className="waste-header">
          <div className="header-top">
            <h1>Waste Tracking</h1>
            <div className="year-selector">
              <label>Year:</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
              >
                {Array.from({ length: 5 }, (_, i) => currentYear - 2 + i).map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>

          {/* YTD Summary Bar */}
          <div className="summary-bar">
            <div className="summary-card">
              <div className="summary-label">Year-End Goal</div>
              <div className="summary-value">
                {editingGoal ? (
                  <div className="goal-edit">
                    <input
                      type="number"
                      value={goalInput}
                      onChange={(e) => setGoalInput(e.target.value)}
                      min="0"
                      step="0.01"
                      className="goal-input"
                      autoFocus
                    />
                    <span className="goal-unit">g/cover</span>
                    <button onClick={handleGoalSave} className="btn-save">Save</button>
                    <button onClick={handleGoalCancel} className="btn-cancel">Cancel</button>
                  </div>
                ) : (
                  <div className="goal-display">
                    <span className="goal-value">{formatDecimal(goal?.target_grams_per_cover)}</span>
                    <span className="goal-unit">g/cover</span>
                    <button onClick={handleGoalEdit} className="btn-edit">Edit</button>
                  </div>
                )}
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-label">YTD Actual</div>
              <div className="summary-value">
                <span className="value-number">
                  {formatDecimal(summary?.ytd_actual_grams_per_cover)}
                </span>
                <span className="value-unit">g/cover</span>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Variance</div>
              <div className={`summary-value ${getVarianceColor(summary?.variance)}`}>
                <span className="value-number">
                  {summary?.variance > 0 ? '+' : ''}{formatDecimal(summary?.variance)}
                </span>
                <span className="value-unit">g/cover</span>
                {summary?.variance_pct !== 0 && (
                  <span className="variance-pct">
                    ({summary?.variance_pct > 0 ? '+' : ''}{formatDecimal(summary?.variance_pct, 1)}%)
                  </span>
                )}
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Total Diversion</div>
              <div className="summary-value">
                <span className="value-number">
                  {formatNumber(Math.round(summary?.total_diversion_grams))}
                </span>
                <span className="value-unit">grams</span>
              </div>
            </div>
          </div>
        </header>

        {/* Monthly Breakdown Table */}
        <div className="table-container">
          <table className="waste-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>F&B Covers</th>
                <th>FTE</th>
                <th>Temp</th>
                <th>Capture %</th>
                <th>Cafe Covers</th>
                <th>Donation (lbs)</th>
                <th>Compost (lbs)</th>
                <th>Total Diversion (g)</th>
                <th>Grams/Cover</th>
                <th>vs Goal</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((metric) => (
                <tr
                  key={metric.month}
                  onClick={() => handleMonthClick(metric)}
                  className="clickable-row"
                >
                  <td className="month-name">{metric.month_name}</td>
                  <td className="data-cell">{formatNumber(metric.fb_covers)}</td>
                  <td className="data-cell">{formatNumber(metric.fte_count)}</td>
                  <td className="data-cell">{formatNumber(metric.temp_count)}</td>
                  <td className="data-cell">
                    {metric.theoretic_capture_pct ? `${formatDecimal(metric.theoretic_capture_pct, 1)}%` : '—'}
                  </td>
                  <td className="data-cell calculated">{formatNumber(metric.cafe_covers)}</td>
                  <td className="data-cell">
                    {formatDecimal(metric.donation_lbs)}
                    {metric.qr_donation_lbs !== metric.donation_lbs && metric.qr_donation_lbs > 0 && (
                      <span className="override-indicator" title="Manually overridden">*</span>
                    )}
                  </td>
                  <td className="data-cell">
                    {formatDecimal(metric.compost_lbs)}
                    {metric.qr_compost_lbs !== metric.compost_lbs && metric.qr_compost_lbs > 0 && (
                      <span className="override-indicator" title="Manually overridden">*</span>
                    )}
                  </td>
                  <td className="data-cell calculated">
                    {formatNumber(Math.round(metric.total_diversion_grams))}
                  </td>
                  <td className="data-cell primary">
                    {formatDecimal(metric.grams_per_cover)}
                  </td>
                  <td className={`data-cell ${getVarianceColor(metric.grams_per_cover - (goal?.target_grams_per_cover || 0))}`}>
                    {metric.grams_per_cover !== null
                      ? `${metric.grams_per_cover > (goal?.target_grams_per_cover || 0) ? '+' : ''}${formatDecimal(metric.grams_per_cover - (goal?.target_grams_per_cover || 0))}`
                      : '—'
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="table-legend">
          <div className="legend-item">
            <span className="legend-icon calculated">•</span>
            <span>Calculated field</span>
          </div>
          <div className="legend-item">
            <span className="legend-icon override">*</span>
            <span>Manually overridden (differs from QR aggregate)</span>
          </div>
          <div className="legend-item">
            <span>Click any row to view and edit details</span>
          </div>
        </div>
      </div>

      {/* Month Detail Modal */}
      {selectedMonth && (
        <MonthDetailModal
          year={selectedYear}
          month={selectedMonth.month}
          goalTarget={goal?.target_grams_per_cover || 0}
          onClose={handleMonthClose}
        />
      )}
    </div>
  );
}

export default Waste;
