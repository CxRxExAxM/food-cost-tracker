import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from '../lib/axios';
import './ImpersonationBanner.css';

export default function ImpersonationBanner() {
  const { user, setToken } = useAuth();
  const navigate = useNavigate();

  if (!user?.impersonating) {
    return null;
  }

  const handleExitImpersonation = async () => {
    try {
      const response = await axios.post('/super-admin/exit-impersonation');
      // Set the original super admin token
      await setToken(response.data.access_token);
      // Navigate back to Super Admin
      navigate('/super-admin/organizations');
    } catch (error) {
      console.error('Error exiting impersonation:', error);
      alert('Error exiting impersonation');
    }
  };

  return (
    <div className="impersonation-banner">
      <div className="impersonation-content">
        <span className="impersonation-icon">⚠️</span>
        <span className="impersonation-text">
          Viewing as <strong>{user.organization_name}</strong> Admin
          {user.original_super_admin_email && (
            <span className="original-user"> (Super Admin: {user.original_super_admin_email})</span>
          )}
        </span>
      </div>
      <button onClick={handleExitImpersonation} className="exit-impersonation-btn">
        Exit Impersonation
      </button>
    </div>
  );
}
