import { useState, useEffect } from 'react';
import axios from '../lib/axios';

/**
 * Dropdown component for selecting units of measure.
 * Fetches units grouped by type (weight, volume, count, etc.)
 */
function UnitSelect({ value, onChange, name = 'unit_id', className = '', disabled = false }) {
  const [units, setUnits] = useState({ groups: {}, all: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUnits = async () => {
      try {
        const response = await axios.get('/units/grouped');
        setUnits(response.data);
      } catch (err) {
        console.error('Error fetching units:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchUnits();
  }, []);

  const handleChange = (e) => {
    const newValue = e.target.value ? parseInt(e.target.value, 10) : null;
    onChange({
      target: {
        name,
        value: newValue
      }
    });
  };

  // Group display names
  const groupLabels = {
    weight: 'Weight',
    volume: 'Volume',
    count: 'Count',
    length: 'Length',
    other: 'Other'
  };

  // Preferred group order
  const groupOrder = ['weight', 'volume', 'count', 'length', 'other'];

  // Sort groups by preferred order
  const sortedGroups = Object.keys(units.groups).sort((a, b) => {
    const indexA = groupOrder.indexOf(a);
    const indexB = groupOrder.indexOf(b);
    return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
  });

  return (
    <select
      name={name}
      value={value || ''}
      onChange={handleChange}
      className={`form-input ${className}`}
      disabled={disabled || loading}
    >
      <option value="">Select unit...</option>
      {sortedGroups.map(groupKey => (
        <optgroup key={groupKey} label={groupLabels[groupKey] || groupKey}>
          {units.groups[groupKey].map(unit => (
            <option key={unit.id} value={unit.id}>
              {unit.abbreviation} ({unit.name})
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

export default UnitSelect;
