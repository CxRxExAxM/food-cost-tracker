import { useState, useEffect } from 'react';
import { format, parseISO } from 'date-fns';
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart
} from 'recharts';
import Navigation from '../../components/Navigation';
import { useToast } from '../../contexts/ToastContext';
import './Potentials.css';

// API helper with auth
const API_BASE = '/api/potentials';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

async function fetchWithAuth(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers
    }
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

// Format a timestamp for display
function formatTimestamp(isoString) {
  if (!isoString) return 'Never';
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

// Generate and open print window for export
async function openExportWindow(dailyData, events) {
  // Fetch group rooms for all dates
  const groupRoomsByDate = {};

  await Promise.all(
    dailyData.map(async (day) => {
      try {
        const res = await fetch(`${API_BASE}/group-rooms/${day.date}`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          const data = await res.json();
          groupRoomsByDate[day.date] = data.data || [];
        }
      } catch (err) {
        console.error(`Error fetching group rooms for ${day.date}:`, err);
        groupRoomsByDate[day.date] = [];
      }
    })
  );

  // Helper functions
  const getEventsForDay = (date) => events.filter(e => e.date === date);

  const groupEventsByBooking = (dayEvents) => {
    const grouped = {};
    dayEvents.forEach(event => {
      if (!grouped[event.booking_name]) grouped[event.booking_name] = [];
      grouped[event.booking_name].push(event);
    });
    return grouped;
  };

  const getGroupRoomData = (date, groupName) => {
    const dayRooms = groupRoomsByDate[date] || [];
    return dayRooms.find(gr => gr.block_name === groupName) || { rooms: 0, arrivals: 0, departures: 0 };
  };

  const getAllGroupsForDay = (date, eventGroupNames) => {
    const dayRooms = groupRoomsByDate[date] || [];
    const significantRoomGroups = dayRooms
      .filter(gr => gr.rooms > 20 || gr.arrivals > 20 || gr.departures > 20)
      .map(gr => gr.block_name);
    return [...new Set([...eventGroupNames, ...significantRoomGroups])];
  };

  // Open print window
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow popups for this site to print');
    return;
  }

  const dateRange = dailyData.length > 0
    ? `${format(parseISO(dailyData[0].date), 'MMM d')} - ${format(parseISO(dailyData[dailyData.length - 1].date), 'MMM d, yyyy')}`
    : '';

  let html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>F&B Running Potentials</title>
      <style>
        @page {
          margin: 0;
          size: letter;
        }
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; padding: 20px; }
        .title { text-align: center; margin-bottom: 20px; }
        .title h1 { font-size: 18px; margin-bottom: 4px; }
        .title p { color: #666; }
        .day { margin-bottom: 24px; page-break-inside: avoid; }
        .day-header { background: #1f2937 !important; color: white; padding: 8px 12px; display: flex; justify-content: space-between; }
        .day-header .stats { display: flex; gap: 12px; }
        .day-header .arr { color: #86efac; }
        .day-header .dep { color: #fca5a5; }
        .meals { display: grid; grid-template-columns: repeat(4, 1fr); border-left: 1px solid #ccc; border-right: 1px solid #ccc; }
        .meal { padding: 8px; text-align: center; border-right: 1px solid #ccc; }
        .meal:last-child { border-right: none; }
        .meal.breakfast { background: #fef3c7 !important; }
        .meal.lunch { background: #d1fae5 !important; }
        .meal.dinner { background: #ede9fe !important; }
        .meal.reception { background: #fce7f3 !important; }
        .meal .label { font-weight: 600; text-transform: uppercase; color: #666; margin-bottom: 4px; }
        .groups { border: 1px solid #ccc; border-top: none; }
        .groups-header { display: flex; padding: 6px 12px; background: #e5e7eb !important; font-weight: 600; font-size: 10px; color: #4b5563; border-bottom: 1px solid #ccc; }
        .group-row { display: flex; padding: 6px 12px; border-bottom: 1px solid #d1d5db; align-items: flex-start; }
        .group-row:last-child { border-bottom: none; }
        .group-row.even { background: white !important; }
        .group-row.odd { background: #f3f4f6 !important; }
        .group-name { flex: 1; font-weight: 500; min-width: 200px; }
        .group-rooms { width: 60px; text-align: right; color: #2563eb; }
        .group-arr { width: 50px; text-align: right; color: #16a34a; }
        .group-dep { width: 50px; text-align: right; color: #dc2626; }
        .group-events { flex: 2; padding-left: 16px; }
        .event { margin-bottom: 2px; }
        .event .cat { font-weight: 500; }
        .event .cat.breakfast { color: #d97706; }
        .event .cat.lunch { color: #059669; }
        .event .cat.dinner { color: #7c3aed; }
        .event .cat.reception { color: #db2777; }
        .event .time { color: #888; margin: 0 8px; }
        .event .venue { color: #666; }
        .no-groups { padding: 12px; color: #888; font-style: italic; }
        @media print {
          body { padding: 0.4in; margin: 0; }
          .day { page-break-inside: avoid; }
        }
      </style>
    </head>
    <body>
      <div class="title">
        <h1>F&B Running Potentials</h1>
        <p>${dateRange}</p>
      </div>
  `;

  dailyData.forEach(day => {
    const dayEvents = getEventsForDay(day.date);
    const groupedEvents = groupEventsByBooking(dayEvents);
    const eventGroupNames = Object.keys(groupedEvents);
    const allGroupNames = getAllGroupsForDay(day.date, eventGroupNames);
    const dayRooms = groupRoomsByDate[day.date] || [];
    const totalArrivals = dayRooms.reduce((sum, gr) => sum + (gr.arrivals || 0), 0);
    const totalDepartures = dayRooms.reduce((sum, gr) => sum + (gr.departures || 0), 0);

    const ihg = day.adults_children || 0;

    html += `
      <div class="day">
        <div class="day-header">
          <strong>${day.day_of_week}, ${format(parseISO(day.date), 'MMMM d, yyyy')}</strong>
          <div class="stats">
            ${day.has_forecast !== false ? `
              <span>Occ: ${day.occupancy_pct}%</span>
              <span>Rooms: ${day.forecasted_rooms}</span>
              <span>IHG: ${day.adults_children}</span>
              <span>Kids: ${day.kids}</span>
              ${totalArrivals > 0 ? `<span class="arr">Arr: ${totalArrivals}</span>` : ''}
              ${totalDepartures > 0 ? `<span class="dep">Dep: ${totalDepartures}</span>` : ''}
            ` : ''}
          </div>
        </div>
        <div class="meals">
          ${['breakfast', 'lunch', 'dinner', 'reception'].map(meal => {
            const catered = day[`catered_${meal}`] || 0;
            const aloo = Math.max(0, ihg - catered);
            return `
              <div class="meal ${meal}">
                <div class="label">${meal}</div>
                <div>Catered: <strong>${catered}</strong></div>
                <div>ALOO: <strong>${aloo}</strong></div>
              </div>
            `;
          }).join('')}
        </div>
        <div class="groups">
          <div class="groups-header">
            <div class="group-name">Group</div>
            <div class="group-rooms">Rooms</div>
            <div class="group-arr">Arr</div>
            <div class="group-dep">Dep</div>
            <div class="group-events">Events</div>
          </div>
          ${allGroupNames.length === 0 ? '<div class="no-groups">No groups</div>' :
            allGroupNames.map((groupName, idx) => {
              const groupEvents = groupedEvents[groupName] || [];
              const roomData = getGroupRoomData(day.date, groupName);
              const rowClass = idx % 2 === 0 ? 'even' : 'odd';

              return `
                <div class="group-row ${rowClass}">
                  <div class="group-name">${groupName}</div>
                  <div class="group-rooms">${roomData.rooms > 0 ? roomData.rooms : '-'}</div>
                  <div class="group-arr">${roomData.arrivals > 0 ? '+' + roomData.arrivals : '-'}</div>
                  <div class="group-dep">${roomData.departures > 0 ? '-' + roomData.departures : '-'}</div>
                  <div class="group-events">
                    ${groupEvents.length > 0 ? groupEvents.map(e => `
                      <div class="event">
                        <span class="cat ${e.category}">${e.category.charAt(0).toUpperCase() + e.category.slice(1)}</span>
                        <span class="time">${e.time}</span>
                        <span>${e.attendees} pax</span>
                        <span class="venue">${e.venue}</span>
                        ${e.notes ? `<div style="color:#666;font-style:italic;margin-left:0;padding-left:4px;margin-top:2px;border-left:2px solid #ddd;">Note: ${e.notes}</div>` : ''}
                      </div>
                    `).join('') : '-'}
                  </div>
                </div>
              `;
            }).join('')
          }
        </div>
      </div>
    `;
  });

  html += `
    </body>
    </html>
  `;

  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
  }, 250);
}

// Format large numbers with commas
function formatNumber(num) {
  if (num === null || num === undefined) return '-';
  return num.toLocaleString();
}

// Chart colors
const COLORS = {
  primary: '#3b82f6',
  secondary: '#10b981',
  accent: '#f59e0b',
  danger: '#ef4444',
  purple: '#8b5cf6',
  pink: '#ec4899',
};

const MEAL_COLORS = {
  breakfast: '#d97706',
  lunch: '#10b981',
  dinner: '#8b5cf6',
  reception: '#ec4899',
};

// Metric card component
function MetricCard({ title, value, subtitle, icon }) {
  return (
    <div className="potentials-metric-card">
      <div className="metric-card-content">
        <div>
          <p className="metric-title">{title}</p>
          <p className="metric-value">{value}</p>
          {subtitle && <p className="metric-subtitle">{subtitle}</p>}
        </div>
        {icon && <div className="metric-icon">{icon}</div>}
      </div>
    </div>
  );
}

// Occupancy chart component
function OccupancyChart({ data }) {
  const chartData = data.map(d => ({
    date: d.day_short + ' ' + format(parseISO(d.date), 'M/d'),
    fullDate: d.date,
    occupancy: d.occupancy_pct || 0,
    rooms: d.forecasted_rooms || 0,
    arrivals: d.arrivals || 0,
    departures: d.departures || 0,
  }));

  return (
    <div className="potentials-chart-card">
      <h3>Occupancy & Room Movement</h3>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
          <YAxis yAxisId="left" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} domain={[0, 100]} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)'
            }}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="arrivals" name="Arrivals" fill={COLORS.secondary} opacity={0.8} />
          <Bar yAxisId="left" dataKey="departures" name="Departures" fill={COLORS.danger} opacity={0.8} />
          <Line yAxisId="right" type="monotone" dataKey="occupancy" name="Occupancy %" stroke={COLORS.primary} strokeWidth={3} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// Meal covers chart component
function MealCoversChart({ data }) {
  const chartData = data.map(d => ({
    date: d.day_short + ' ' + format(parseISO(d.date), 'M/d'),
    breakfast: d.catered_breakfast || 0,
    lunch: d.catered_lunch || 0,
    dinner: d.catered_dinner || 0,
    reception: d.catered_reception || 0,
    total: d.total_catered_covers || 0,
  }));

  return (
    <div className="potentials-chart-card">
      <h3>F&B Catered Covers by Meal Period</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)'
            }}
          />
          <Legend />
          <Bar dataKey="breakfast" name="Breakfast" stackId="a" fill={MEAL_COLORS.breakfast} />
          <Bar dataKey="lunch" name="Lunch" stackId="a" fill={MEAL_COLORS.lunch} />
          <Bar dataKey="dinner" name="Dinner" stackId="a" fill={MEAL_COLORS.dinner} />
          <Bar dataKey="reception" name="Reception" stackId="a" fill={MEAL_COLORS.reception} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Date selector component
function DateSelector({ dates, selectedDate, onSelect }) {
  return (
    <div className="date-selector">
      {dates.map(d => {
        const dateObj = parseISO(d.date);
        const isSelected = d.date === selectedDate;
        const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
        const hasForecast = d.has_forecast !== false;
        const hasEvents = d.total_catered_covers > 0;

        let className = 'date-btn';
        if (isSelected) className += ' selected';
        else if (!hasForecast) className += ' no-forecast';
        else if (isWeekend) className += ' weekend';

        return (
          <button
            key={d.date}
            onClick={() => onSelect(d.date)}
            className={className}
            title={!hasForecast ? 'No forecast data for this date' : ''}
          >
            <span className="date-day">{d.day_short}</span>
            <span className="date-num">{format(dateObj, 'M/d')}</span>
            {hasEvents && <div className="date-indicator"></div>}
          </button>
        );
      })}
    </div>
  );
}

// Event row component
function EventRow({ event, onEventUpdate, onEventDelete }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { showToast } = useToast();

  const startEditing = () => {
    setEditData({
      booking_name: event.booking_name || '',
      event_name: event.event_name || '',
      time: event.time || '',
      attendees: event.attendees || 0,
      venue: event.venue || '',
      notes: event.notes || ''
    });
    setIsEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetchWithAuth(`${API_BASE}/events/${event.event_id}`, {
        method: 'PUT',
        body: JSON.stringify(editData)
      });
      onEventUpdate(event.event_id, editData);
      setIsEditing(false);
      showToast('Event updated', 'success');
    } catch (err) {
      showToast('Failed to save: ' + err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await fetchWithAuth(`${API_BASE}/events/${event.event_id}`, {
        method: 'DELETE'
      });
      onEventDelete(event.event_id);
      showToast('Event deleted', 'success');
    } catch (err) {
      showToast('Failed to delete: ' + err.message, 'error');
    }
    setShowDeleteConfirm(false);
  };

  if (showDeleteConfirm) {
    return (
      <div className="event-row delete-confirm">
        <span>Delete "{event.booking_name} - {event.event_name}"?</span>
        <div className="event-actions">
          <button onClick={handleDelete} className="btn-danger-sm">Delete</button>
          <button onClick={() => setShowDeleteConfirm(false)} className="btn-ghost-sm">Cancel</button>
        </div>
      </div>
    );
  }

  if (isEditing) {
    return (
      <div className="event-row editing">
        <div className="edit-form">
          <div className="edit-grid">
            <div>
              <label>Group</label>
              <input
                type="text"
                value={editData.booking_name}
                onChange={(e) => setEditData({ ...editData, booking_name: e.target.value })}
              />
            </div>
            <div>
              <label>Event Name</label>
              <input
                type="text"
                value={editData.event_name}
                onChange={(e) => setEditData({ ...editData, event_name: e.target.value })}
              />
            </div>
            <div>
              <label>Time</label>
              <input
                type="text"
                value={editData.time}
                onChange={(e) => setEditData({ ...editData, time: e.target.value })}
              />
            </div>
            <div>
              <label>Attendees</label>
              <input
                type="number"
                value={editData.attendees}
                onChange={(e) => setEditData({ ...editData, attendees: parseInt(e.target.value) || 0 })}
              />
            </div>
            <div>
              <label>Venue</label>
              <input
                type="text"
                value={editData.venue}
                onChange={(e) => setEditData({ ...editData, venue: e.target.value })}
              />
            </div>
            <div>
              <label>Notes</label>
              <input
                type="text"
                value={editData.notes}
                onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
              />
            </div>
          </div>
          <div className="edit-actions">
            <button onClick={handleSave} disabled={saving} className="btn-primary-sm">
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setIsEditing(false)} className="btn-ghost-sm">Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="event-row">
      <div className={`event-dot ${event.category}`}></div>
      <div className="event-info">
        <span className="event-name">{event.booking_name}</span>
        {event.event_name && <span className="event-desc"> - {event.event_name}</span>}
      </div>
      <div className="event-time">{event.time}</div>
      <div className="event-pax">{event.attendees || event.gtd || '-'} pax</div>
      <div className="event-venue">{event.venue}</div>
      <div className="event-actions">
        <button onClick={startEditing} className="btn-ghost-sm">Edit</button>
        <button onClick={() => setShowDeleteConfirm(true)} className="btn-ghost-sm danger">Delete</button>
      </div>
      {event.notes && <div className="event-notes">Note: {event.notes}</div>}
    </div>
  );
}

// Add event form
function AddEventForm({ date, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    date: date,
    booking_name: '',
    event_name: '',
    category: 'breakfast',
    time: '',
    attendees: 0,
    venue: '',
    notes: ''
  });
  const [saving, setSaving] = useState(false);
  const { showToast } = useToast();

  const handleSave = async () => {
    if (!formData.booking_name) {
      showToast('Group name is required', 'error');
      return;
    }
    setSaving(true);
    try {
      const data = await fetchWithAuth(`${API_BASE}/events`, {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      onSave({ ...formData, event_id: data.event_id });
      showToast('Event created', 'success');
    } catch (err) {
      showToast('Failed to create event: ' + err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="add-event-form">
      <div className="form-header">Add New Event</div>
      <div className="edit-grid">
        <div>
          <label>Group *</label>
          <input
            type="text"
            value={formData.booking_name}
            onChange={(e) => setFormData({ ...formData, booking_name: e.target.value })}
            placeholder="Group name"
          />
        </div>
        <div>
          <label>Event Name</label>
          <input
            type="text"
            value={formData.event_name}
            onChange={(e) => setFormData({ ...formData, event_name: e.target.value })}
            placeholder="Event description"
          />
        </div>
        <div>
          <label>Category *</label>
          <select
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          >
            <option value="breakfast">Breakfast</option>
            <option value="lunch">Lunch</option>
            <option value="dinner">Dinner</option>
            <option value="reception">Reception</option>
          </select>
        </div>
        <div>
          <label>Time</label>
          <input
            type="text"
            value={formData.time}
            onChange={(e) => setFormData({ ...formData, time: e.target.value })}
            placeholder="e.g. 07:00 - 09:00"
          />
        </div>
        <div>
          <label>Attendees</label>
          <input
            type="number"
            value={formData.attendees}
            onChange={(e) => setFormData({ ...formData, attendees: parseInt(e.target.value) || 0 })}
          />
        </div>
        <div>
          <label>Venue</label>
          <input
            type="text"
            value={formData.venue}
            onChange={(e) => setFormData({ ...formData, venue: e.target.value })}
            placeholder="Location"
          />
        </div>
      </div>
      <div className="edit-actions">
        <button onClick={handleSave} disabled={saving} className="btn-primary-sm">
          {saving ? 'Adding...' : 'Add Event'}
        </button>
        <button onClick={onCancel} className="btn-ghost-sm">Cancel</button>
      </div>
    </div>
  );
}

// Day detail component
function DayDetail({ date, events, dailyData, onEventUpdate, onEventDelete, onEventAdd }) {
  const [showAddForm, setShowAddForm] = useState(false);
  const dayInfo = dailyData.find(d => d.date === date);
  const dayEvents = events.filter(e => e.date === date);

  const handleAddEvent = (newEvent) => {
    onEventAdd(newEvent);
    setShowAddForm(false);
  };

  if (!dayInfo) return null;

  const hasForecast = dayInfo.has_forecast !== false;
  const ihg = Math.round(dayInfo.adults_children || 0);

  return (
    <div className="potentials-card day-detail">
      <div className="day-detail-header">
        <div>
          <h3>{dayInfo.day_of_week}, {format(parseISO(date), 'MMMM d, yyyy')}</h3>
          {!hasForecast && <p className="no-forecast-warning">No forecast data available for this date</p>}
        </div>
        <div className="day-stats">
          {hasForecast ? (
            <>
              <span>Occupancy: <strong>{dayInfo.occupancy_pct}%</strong></span>
              <span>Rooms: <strong>{formatNumber(dayInfo.forecasted_rooms)}</strong></span>
              <span>Kids: <strong>{formatNumber(dayInfo.kids || 0)}</strong></span>
            </>
          ) : (
            <span className="forecast-pending">Forecast pending</span>
          )}
        </div>
      </div>

      <div className="meal-summary-grid">
        {['breakfast', 'lunch', 'dinner', 'reception'].map(meal => {
          const catered = Math.round(dayInfo[`catered_${meal}`] || 0);
          const aloo = Math.max(0, ihg - catered);

          return (
            <div key={meal} className={`meal-card ${meal}`}>
              <div className="meal-label">{meal}</div>
              <div className="meal-stats">
                <div><span>IHG</span><strong>{formatNumber(ihg)}</strong></div>
                <div><span>Catered</span><strong className="catered">{formatNumber(catered)}</strong></div>
                <div><span>ALOO</span><strong>{formatNumber(aloo)}</strong></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="events-section">
        <div className="events-header">
          <span>Events</span>
          {!showAddForm && (
            <button onClick={() => setShowAddForm(true)} className="btn-primary-sm">+ Add Event</button>
          )}
        </div>

        {showAddForm && (
          <AddEventForm
            date={date}
            onSave={handleAddEvent}
            onCancel={() => setShowAddForm(false)}
          />
        )}

        <div className="events-list">
          {dayEvents.length === 0 && !showAddForm ? (
            <p className="no-events">No catered events for this date</p>
          ) : (
            dayEvents.map((event) => (
              <EventRow
                key={event.event_id}
                event={event}
                onEventUpdate={onEventUpdate}
                onEventDelete={onEventDelete}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// Groups timeline component
function GroupsTimeline({ selectedDate, events, groupRooms }) {
  if (!selectedDate) return null;

  const dayEvents = events.filter(e => e.date === selectedDate);
  const roomsByName = {};
  groupRooms.forEach(gr => { roomsByName[gr.block_name] = gr; });

  const eventGroupNames = [...new Set(dayEvents.map(e => e.booking_name))];
  const roomGroupNames = groupRooms.map(gr => gr.block_name);
  const allGroupNames = [...new Set([...eventGroupNames, ...roomGroupNames])];

  const groupsForDay = allGroupNames.map(groupName => {
    const roomData = roomsByName[groupName] || { rooms: 0, arrivals: 0, departures: 0 };
    const todayGroupEvents = dayEvents.filter(e => e.booking_name === groupName);

    const mealCovers = { breakfast: 0, lunch: 0, dinner: 0, reception: 0 };
    todayGroupEvents.forEach(e => {
      if (e.category in mealCovers) {
        mealCovers[e.category] += e.attendees || 0;
      }
    });

    return {
      name: groupName,
      rooms: roomData.rooms,
      arrivals: roomData.arrivals,
      departures: roomData.departures,
      events_today: todayGroupEvents.length,
      meal_covers: mealCovers,
    };
  }).sort((a, b) => b.rooms - a.rooms || a.name.localeCompare(b.name));

  const totalRooms = groupsForDay.reduce((sum, g) => sum + g.rooms, 0);
  const totalArrivals = groupsForDay.reduce((sum, g) => sum + g.arrivals, 0);
  const totalDepartures = groupsForDay.reduce((sum, g) => sum + g.departures, 0);

  return (
    <div className="potentials-card groups-timeline">
      <div className="groups-header">
        <h3>Groups In-House - {format(parseISO(selectedDate), 'EEEE, MMM d')}</h3>
        <div className="groups-summary">
          <span>{groupsForDay.length} groups</span>
          <span className="rooms">{formatNumber(totalRooms)} rooms</span>
          {totalArrivals > 0 && <span className="arrivals">{formatNumber(totalArrivals)} arriving</span>}
          {totalDepartures > 0 && <span className="departures">{formatNumber(totalDepartures)} departing</span>}
        </div>
      </div>

      {groupsForDay.length === 0 ? (
        <p className="no-groups">No groups in-house for this date</p>
      ) : (
        <div className="groups-table-wrapper">
          <table className="groups-table">
            <thead>
              <tr>
                <th>Group</th>
                <th>Rooms</th>
                <th>Arr</th>
                <th>Dep</th>
                <th>Events</th>
                <th>Breakfast</th>
                <th>Lunch</th>
                <th>Dinner</th>
                <th>Reception</th>
              </tr>
            </thead>
            <tbody>
              {groupsForDay.map((group, idx) => (
                <tr key={idx}>
                  <td className="group-name">{group.name}</td>
                  <td className="rooms">{group.rooms > 0 ? formatNumber(group.rooms) : '-'}</td>
                  <td className="arrivals">{group.arrivals > 0 ? formatNumber(group.arrivals) : '-'}</td>
                  <td className="departures">{group.departures > 0 ? formatNumber(group.departures) : '-'}</td>
                  <td className="events">{group.events_today > 0 ? group.events_today : '-'}</td>
                  <td className="breakfast">{group.meal_covers.breakfast > 0 ? formatNumber(group.meal_covers.breakfast) : '-'}</td>
                  <td className="lunch">{group.meal_covers.lunch > 0 ? formatNumber(group.meal_covers.lunch) : '-'}</td>
                  <td className="dinner">{group.meal_covers.dinner > 0 ? formatNumber(group.meal_covers.dinner) : '-'}</td>
                  <td className="reception">{group.meal_covers.reception > 0 ? formatNumber(group.meal_covers.reception) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Upload modal component
function UploadModal({ isOpen, onClose, onUploadComplete }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState([]);
  const { showToast } = useToast();

  if (!isOpen) return null;

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    await processFiles(files);
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    await processFiles(files);
  };

  const processFiles = async (files) => {
    setUploading(true);
    setResults([]);
    const newResults = [];

    for (const file of files) {
      if (!file.name.endsWith('.xlsx')) {
        newResults.push({ file: file.name, status: 'error', message: 'Not an Excel file' });
        continue;
      }

      const isHitlist = file.name.toLowerCase().includes('hit list');
      const isForecast = file.name.toLowerCase().includes('forecast');

      if (!isHitlist && !isForecast) {
        newResults.push({
          file: file.name,
          status: 'error',
          message: 'Filename must contain "Hit List" or "Forecast"'
        });
        continue;
      }

      const endpoint = isHitlist ? 'hitlist' : 'forecast';
      const formData = new FormData();
      formData.append('file', file);

      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE}/upload/${endpoint}`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });
        const data = await res.json();

        if (res.ok) {
          if (isHitlist) {
            newResults.push({
              file: file.name,
              status: 'success',
              message: `${data.events_added} events added, ${data.events_skipped} skipped`
            });
          } else {
            newResults.push({
              file: file.name,
              status: 'success',
              message: `${data.metrics_added} added, ${data.metrics_updated} updated`
            });
          }
        } else {
          newResults.push({ file: file.name, status: 'error', message: data.detail });
        }
      } catch (err) {
        newResults.push({ file: file.name, status: 'error', message: err.message });
      }
    }

    setResults(newResults);
    setUploading(false);

    if (newResults.some(r => r.status === 'success')) {
      onUploadComplete();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Files</h2>
          <button onClick={onClose} className="modal-close">&times;</button>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`drop-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
        >
          {uploading ? (
            <div className="uploading-text">Uploading...</div>
          ) : (
            <>
              <div className="drop-icon">📁</div>
              <p>Drag & drop Excel files here</p>
              <p className="drop-hint">or</p>
              <label className="file-input-label">
                Choose Files
                <input
                  type="file"
                  multiple
                  accept=".xlsx"
                  onChange={handleFileSelect}
                  className="file-input"
                />
              </label>
            </>
          )}
        </div>

        <div className="file-naming-hint">
          <strong>File naming:</strong>
          <ul>
            <li>Hitlist files must contain "Hit List" in filename</li>
            <li>Forecast files must contain "Forecast" in filename</li>
          </ul>
        </div>

        {results.length > 0 && (
          <div className="upload-results">
            {results.map((r, i) => (
              <div key={i} className={`upload-result ${r.status}`}>
                <strong>{r.file}:</strong> {r.message}
              </div>
            ))}
          </div>
        )}

        <div className="modal-footer">
          <button onClick={onClose} className="btn-secondary">Close</button>
        </div>
      </div>
    </div>
  );
}

// Date range filter component
function DateRangeFilter({ startDate, endDate, minDate, maxDate, onStartChange, onEndChange, onReset }) {
  const isFullRange = startDate === minDate && endDate === maxDate;

  const generateDateOptions = (minD, maxD) => {
    const options = [];
    let current = parseISO(minD);
    const end = parseISO(maxD);

    while (current <= end) {
      const value = format(current, 'yyyy-MM-dd');
      const label = format(current, 'EEE, MMM d');
      options.push({ value, label });
      current = new Date(current.getTime() + 24 * 60 * 60 * 1000);
    }
    return options;
  };

  return (
    <div className="date-range-filter">
      <div className="filter-group">
        <label>From:</label>
        <select value={startDate} onChange={(e) => onStartChange(e.target.value)}>
          {generateDateOptions(minDate, endDate || maxDate).map(d => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>
      </div>
      <div className="filter-group">
        <label>To:</label>
        <select value={endDate} onChange={(e) => onEndChange(e.target.value)}>
          {generateDateOptions(startDate || minDate, maxDate).map(d => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>
      </div>
      {!isFullRange && (
        <button onClick={onReset} className="reset-filter">Reset</button>
      )}
    </div>
  );
}

// Loading spinner
function LoadingSpinner() {
  return (
    <div className="potentials-loading">
      <div className="spinner"></div>
    </div>
  );
}

// Error message
function ErrorMessage({ message }) {
  return (
    <div className="potentials-error">
      <p className="error-title">Error loading data</p>
      <p className="error-message">{message}</p>
      <p className="error-hint">Make sure you're logged in and the backend is running.</p>
    </div>
  );
}

// Main Potentials component
function Potentials() {
  const [metrics, setMetrics] = useState(null);
  const [dailySummary, setDailySummary] = useState([]);
  const [allDailySummary, setAllDailySummary] = useState([]);
  const [events, setEvents] = useState([]);
  const [allEvents, setAllEvents] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filterStartDate, setFilterStartDate] = useState(() => {
    return localStorage.getItem('potentials_filter_start') || '';
  });
  const [filterEndDate, setFilterEndDate] = useState(() => {
    return localStorage.getItem('potentials_filter_end') || '';
  });
  const [dateRange, setDateRange] = useState({ min: '', max: '' });

  // Persist filter dates to localStorage
  useEffect(() => {
    if (filterStartDate) {
      localStorage.setItem('potentials_filter_start', filterStartDate);
    }
  }, [filterStartDate]);

  useEffect(() => {
    if (filterEndDate) {
      localStorage.setItem('potentials_filter_end', filterEndDate);
    }
  }, [filterEndDate]);

  const [status, setStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [groupRooms, setGroupRooms] = useState([]);

  const { showToast } = useToast();

  // Fetch all data on mount
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        const [metricsData, dailyData, eventsData, groupsData, statusData] = await Promise.all([
          fetchWithAuth(`${API_BASE}/metrics`),
          fetchWithAuth(`${API_BASE}/daily-summary`),
          fetchWithAuth(`${API_BASE}/events`),
          fetchWithAuth(`${API_BASE}/groups`),
          fetchWithAuth(`${API_BASE}/status`),
        ]);

        setStatus(statusData);
        setMetrics(metricsData);
        setDailySummary(dailyData.data);
        setAllDailySummary(dailyData.data);
        setEvents(eventsData.data);
        setAllEvents(eventsData.data);
        setGroups(groupsData.data);

        if (dailyData.data.length > 0) {
          const dataMin = dailyData.data[0].date;
          const dataMax = dailyData.data[dailyData.data.length - 1].date;

          setDateRange({ min: dataMin, max: dataMax });

          // Only set filter dates if not already loaded from localStorage
          // or if persisted dates are outside the current data range
          const savedStart = localStorage.getItem('potentials_filter_start');
          const savedEnd = localStorage.getItem('potentials_filter_end');

          if (!savedStart || savedStart < dataMin || savedStart > dataMax) {
            setFilterStartDate(dataMin);
          }
          if (!savedEnd || savedEnd < dataMin || savedEnd > dataMax) {
            setFilterEndDate(dataMax);
          }

          const firstWithEvents = dailyData.data.find(d => d.event_count > 0);
          setSelectedDate(firstWithEvents?.date || dailyData.data[0].date);
        }

        setError(null);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  // Fetch group rooms when selected date changes
  useEffect(() => {
    if (!selectedDate) {
      setGroupRooms([]);
      return;
    }

    async function fetchGroupRooms() {
      try {
        const data = await fetchWithAuth(`${API_BASE}/group-rooms/${selectedDate}`);
        setGroupRooms(data.data || []);
      } catch (err) {
        console.error('Error fetching group rooms:', err);
        setGroupRooms([]);
      }
    }

    fetchGroupRooms();
  }, [selectedDate]);

  // Filter data when date range changes
  useEffect(() => {
    if (!allDailySummary.length) return;

    const filteredDaily = allDailySummary.filter(d => {
      if (filterStartDate && d.date < filterStartDate) return false;
      if (filterEndDate && d.date > filterEndDate) return false;
      return true;
    });
    setDailySummary(filteredDaily);

    const filteredEvents = allEvents.filter(e => {
      if (!e.date) return false;
      if (filterStartDate && e.date < filterStartDate) return false;
      if (filterEndDate && e.date > filterEndDate) return false;
      return true;
    });
    setEvents(filteredEvents);

    if (selectedDate && (selectedDate < filterStartDate || selectedDate > filterEndDate)) {
      const firstWithEvents = filteredDaily.find(d => d.event_count > 0);
      setSelectedDate(firstWithEvents?.date || filteredDaily[0]?.date || null);
    }
  }, [filterStartDate, filterEndDate, allDailySummary, allEvents, selectedDate]);

  const resetDateFilter = () => {
    setFilterStartDate(dateRange.min);
    setFilterEndDate(dateRange.max);
  };

  const handleEventUpdate = (eventId, updatedFields) => {
    const updateEvents = (eventsList) =>
      eventsList.map(e => e.event_id === eventId ? { ...e, ...updatedFields } : e);

    setEvents(updateEvents(events));
    setAllEvents(updateEvents(allEvents));
  };

  const handleEventAdd = (newEvent) => {
    const addEvent = (eventsList) => [...eventsList, newEvent];
    setEvents(addEvent(events));
    setAllEvents(addEvent(allEvents));

    const updatedDaily = allDailySummary.map(day => {
      if (day.date === newEvent.date) {
        const cateredKey = `catered_${newEvent.category}`;
        return {
          ...day,
          [cateredKey]: (day[cateredKey] || 0) + (newEvent.attendees || 0),
          total_catered_covers: (day.total_catered_covers || 0) + (newEvent.attendees || 0),
          event_count: (day.event_count || 0) + 1
        };
      }
      return day;
    });
    setAllDailySummary(updatedDaily);
    setDailySummary(updatedDaily.filter(d =>
      d.date >= filterStartDate && d.date <= filterEndDate
    ));
  };

  const handleEventDelete = (eventId) => {
    const filterEvents = (eventsList) =>
      eventsList.filter(e => e.event_id !== eventId);

    setEvents(filterEvents(events));
    setAllEvents(filterEvents(allEvents));
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchWithAuth(`${API_BASE}/refresh`, { method: 'POST' });

      const [dailyData, eventsData, groupsData, statusData] = await Promise.all([
        fetchWithAuth(`${API_BASE}/daily-summary`),
        fetchWithAuth(`${API_BASE}/events`),
        fetchWithAuth(`${API_BASE}/groups`),
        fetchWithAuth(`${API_BASE}/status`),
      ]);

      setAllDailySummary(dailyData.data);
      setDailySummary(dailyData.data);
      setAllEvents(eventsData.data);
      setEvents(eventsData.data);
      setGroups(groupsData.data);
      setStatus(statusData);

      if (dailyData.data.length > 0) {
        const newMin = dailyData.data[0].date;
        const newMax = dailyData.data[dailyData.data.length - 1].date;
        setDateRange({ min: newMin, max: newMax });
        setFilterStartDate(newMin);
        setFilterEndDate(newMax);
      }

      showToast('Data refreshed', 'success');
    } catch (err) {
      console.error('Refresh failed:', err);
      showToast('Failed to refresh data', 'error');
    } finally {
      setRefreshing(false);
    }
  };

  const filteredMetrics = dailySummary.length > 0 ? {
    total_days: dailySummary.length,
    date_range: {
      start: dailySummary[0]?.date,
      end: dailySummary[dailySummary.length - 1]?.date,
    },
    avg_occupancy_pct: Math.round(
      dailySummary.reduce((sum, d) => sum + (d.occupancy_pct || 0), 0) / dailySummary.length * 10
    ) / 10,
    total_catered_covers: dailySummary.reduce((sum, d) => sum + d.total_catered_covers, 0),
    total_events: dailySummary.reduce((sum, d) => sum + d.event_count, 0),
    total_groups: groups.length,
    peak_day: dailySummary.reduce((max, d) =>
      d.total_catered_covers > (max?.total_catered_covers || 0) ? d : max, null
    ),
  } : metrics;

  if (loading) {
    return (
      <div className="potentials-page">
        <Navigation />
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="potentials-page">
        <Navigation />
        <div className="potentials-container">
          <ErrorMessage message={error} />
        </div>
      </div>
    );
  }

  return (
    <div className="potentials-page">
      <Navigation />

      <header className="potentials-header">
        <div className="header-content">
          <div className="header-title">
            <h1>F&B Planning Dashboard</h1>
            {filteredMetrics?.date_range && (
              <p>
                Showing {filteredMetrics.total_days} days: {format(parseISO(filteredMetrics.date_range.start), 'MMM d')} - {format(parseISO(filteredMetrics.date_range.end), 'MMM d, yyyy')}
              </p>
            )}
          </div>
          <div className="header-actions">
            {dateRange.min && (
              <DateRangeFilter
                startDate={filterStartDate}
                endDate={filterEndDate}
                minDate={dateRange.min}
                maxDate={dateRange.max}
                onStartChange={setFilterStartDate}
                onEndChange={setFilterEndDate}
                onReset={resetDateFilter}
              />
            )}
            <button
              onClick={() => openExportWindow(dailySummary, events)}
              disabled={dailySummary.length === 0}
              className="btn-secondary"
            >
              Export
            </button>
            <button onClick={() => setShowUploadModal(true)} className="btn-success">
              Upload Files
            </button>
            <button onClick={handleRefresh} disabled={refreshing} className="btn-primary">
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        {status && (
          <div className="status-bar">
            <span><strong>Hitlist:</strong> {status.last_hitlist_import ? formatTimestamp(status.last_hitlist_import.imported_at) : 'No data'}</span>
            <span><strong>Forecast:</strong> {status.last_forecast_import ? formatTimestamp(status.last_forecast_import.imported_at) : 'No data'}</span>
            <span><strong>Total Events:</strong> {status.totals?.events || 0}</span>
          </div>
        )}
      </header>

      <main className="potentials-container">
        {filteredMetrics && (
          <div className="metrics-grid">
            <MetricCard title="Avg Occupancy" value={`${filteredMetrics.avg_occupancy_pct}%`} icon="🏨" />
            <MetricCard title="Total Groups" value={filteredMetrics.total_groups} icon="👥" />
            <MetricCard title="Total Events" value={formatNumber(filteredMetrics.total_events)} icon="📅" />
            <MetricCard title="Total Catered Covers" value={formatNumber(filteredMetrics.total_catered_covers)} icon="🍽️" />
            <MetricCard title="Peak Day" value={filteredMetrics.peak_day ? format(parseISO(filteredMetrics.peak_day.date), 'MMM d') : '-'} subtitle={filteredMetrics.peak_day ? `${formatNumber(filteredMetrics.peak_day.total_catered_covers)} covers` : ''} icon="📈" />
            <MetricCard title="Days Shown" value={`${filteredMetrics.total_days} days`} icon="📆" />
          </div>
        )}

        <div className="potentials-card date-selector-card">
          <DateSelector
            dates={dailySummary}
            selectedDate={selectedDate}
            onSelect={setSelectedDate}
          />
        </div>

        <div className="charts-grid">
          <OccupancyChart data={dailySummary} />
          <MealCoversChart data={dailySummary} />
        </div>

        {selectedDate && (
          <DayDetail
            date={selectedDate}
            events={events}
            dailyData={dailySummary}
            onEventUpdate={handleEventUpdate}
            onEventDelete={handleEventDelete}
            onEventAdd={handleEventAdd}
          />
        )}

        <GroupsTimeline
          selectedDate={selectedDate}
          events={events}
          groupRooms={groupRooms}
        />
      </main>

      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadComplete={handleRefresh}
      />
    </div>
  );
}

export default Potentials;
