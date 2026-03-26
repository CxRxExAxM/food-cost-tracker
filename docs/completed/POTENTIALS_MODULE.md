# Potentials Module - Completion Documentation

**Completed:** February 2026
**Status:** Production

---

## Overview

F&B Planning Dashboard for daily operations forecasting. Integrates with Opera PMS data exports to provide daily operational insights for food and beverage operations.

---

## Features Implemented

### Data Import
- Opera PMS forecast file imports (Excel)
- Hit list imports for events
- Duplicate detection and handling
- Import history tracking

### Dashboard Views
- Daily occupancy and ADR charts
- Catered covers by meal period
- Group rooms tracking (arrivals/departures)
- Event calendar view

### Data Fields
- **Forecast Metrics:** forecasted_rooms, occupancy_pct, adr, adults_children (IHG), kids, leisure_guests, arrivals, departures
- **Events:** breakfast/lunch/dinner/reception covers, group names, venues, times, attendees, notes

### API Endpoints
- 20+ endpoints for events, forecasts, and group data
- Daily summary aggregation
- Period comparison

---

## Files Modified

### Backend
- `api/app/routers/potentials.py` - Main router (~800 lines)
- Database tables: `property_events`, `forecast_metrics`, `group_rooms`, `import_logs`
- Multiple Alembic migrations for schema

### Frontend
- `frontend/src/pages/Potentials/Potentials.jsx` - Main dashboard (~50KB)
- Charts, date navigation, event details
- CSS: `Potentials.css`

---

## Database Schema

```sql
property_events
  - id, outlet_id, event_date
  - event_name, venue, start_time, end_time
  - attendees, breakfast/lunch/dinner/reception_covers
  - notes, source

forecast_metrics
  - id, outlet_id, forecast_date
  - forecasted_rooms, occupancy_pct, adr
  - adults_children, kids, leisure_guests
  - transient_rooms, arrivals, departures

group_rooms
  - id, outlet_id, business_date
  - group_name, rooms, arrivals, departures

import_logs
  - id, outlet_id, import_type, filename
  - records_processed, status, created_at
```

---

## Integration Points

- **NL Chat Agent:** Potentials data exposed via chat tools
- **Opera PMS:** Import format support
- **Future:** Group resume ingestion (Phase 2)

---

## Notes

- leisure_guests calculated as: transient_rooms × 2.5
- Events support user notes for operational context
- Data feeds into daily operational briefs (planned)
