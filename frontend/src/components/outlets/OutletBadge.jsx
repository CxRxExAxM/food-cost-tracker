import { useOutlet } from '../../contexts/OutletContext';
import './OutletBadge.css';

export default function OutletBadge({ outletId, outletName }) {
  const { outlets } = useOutlet();

  // If outlet name is provided, use it directly
  // Otherwise, look up the outlet by ID
  const displayName = outletName || outlets.find(o => o.id === outletId)?.name || 'Unknown Outlet';

  if (!outletId && !outletName) {
    return null;
  }

  return (
    <span className="outlet-badge">
      <span className="outlet-badge-icon">🏢</span>
      <span className="outlet-badge-text">{displayName}</span>
    </span>
  );
}
