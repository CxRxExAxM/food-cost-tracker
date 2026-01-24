import { useState, useEffect } from 'react';
import axios from '../lib/axios';

/**
 * Dropdown component for selecting vessels.
 * Shows vessel name with capacity hint.
 */
function VesselSelect({ value, onChange, name = 'vessel_id', className = '', disabled = false, showCapacityHint = true }) {
  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVessels = async () => {
      try {
        const response = await axios.get('/vessels');
        setVessels(response.data.vessels || []);
      } catch (err) {
        console.error('Error fetching vessels:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchVessels();
  }, []);

  const handleChange = (e) => {
    const newValue = e.target.value ? parseInt(e.target.value, 10) : null;
    // Also pass the selected vessel object for convenience
    const selectedVessel = vessels.find(v => v.id === newValue);
    onChange({
      target: {
        name,
        value: newValue,
        vessel: selectedVessel || null
      }
    });
  };

  // Format capacity hint
  const formatCapacityHint = (vessel) => {
    if (!vessel.default_capacity) return '';
    const capacity = parseFloat(vessel.default_capacity);
    const unit = vessel.default_unit_abbr || '';
    return ` (${capacity} ${unit})`;
  };

  return (
    <select
      name={name}
      value={value || ''}
      onChange={handleChange}
      className={`form-input ${className}`}
      disabled={disabled || loading}
    >
      <option value="">Select vessel...</option>
      {vessels.map(vessel => (
        <option key={vessel.id} value={vessel.id}>
          {vessel.name}{showCapacityHint ? formatCapacityHint(vessel) : ''}
        </option>
      ))}
    </select>
  );
}

export default VesselSelect;
