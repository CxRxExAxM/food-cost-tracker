import { createContext, useContext, useState, useEffect } from 'react';
import { outletsAPI } from '../services/api/outlets';
import { useAuth } from '../context/AuthContext';

const OutletContext = createContext();

export function useOutlet() {
  const context = useContext(OutletContext);
  if (!context) {
    throw new Error('useOutlet must be used within an OutletProvider');
  }
  return context;
}

export function OutletProvider({ children }) {
  const { user } = useAuth();
  const [outlets, setOutlets] = useState([]);
  const [currentOutlet, setCurrentOutlet] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch outlets when user changes
  useEffect(() => {
    if (user) {
      fetchOutlets();
    } else {
      // User logged out - reset state
      setOutlets([]);
      setCurrentOutlet(null);
      setLoading(false);
    }
  }, [user]);

  // Fetch outlets from API
  const fetchOutlets = async () => {
    try {
      setLoading(true);
      const response = await outletsAPI.list();
      const fetchedOutlets = response.data.outlets || [];
      setOutlets(fetchedOutlets);

      // Restore previously selected outlet from localStorage
      const savedOutletId = localStorage.getItem('selectedOutletId');

      if (savedOutletId === 'all') {
        // "All Outlets" selection (for org-wide admins)
        setCurrentOutlet({ id: 'all', name: 'All Outlets' });
      } else if (savedOutletId && fetchedOutlets.length > 0) {
        // Find the saved outlet
        const savedOutlet = fetchedOutlets.find(o => o.id === parseInt(savedOutletId));
        if (savedOutlet) {
          setCurrentOutlet(savedOutlet);
        } else {
          // Saved outlet not found, default to first outlet
          setCurrentOutlet(fetchedOutlets[0]);
        }
      } else if (fetchedOutlets.length > 0) {
        // No saved selection, default to first outlet
        setCurrentOutlet(fetchedOutlets[0]);
      }

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch outlets:', error);
      setLoading(false);
    }
  };

  // Select an outlet
  const selectOutlet = (outlet) => {
    setCurrentOutlet(outlet);

    // Persist selection in localStorage
    if (outlet.id === 'all') {
      localStorage.setItem('selectedOutletId', 'all');
    } else {
      localStorage.setItem('selectedOutletId', outlet.id.toString());
    }
  };

  // Create new outlet (admin only)
  const createOutlet = async (outletData) => {
    const response = await outletsAPI.create(outletData);
    await fetchOutlets(); // Refresh list
    return response.data;
  };

  // Update outlet (admin only)
  const updateOutlet = async (outletId, updates) => {
    const response = await outletsAPI.update(outletId, updates);
    await fetchOutlets(); // Refresh list
    return response.data;
  };

  // Delete outlet (admin only)
  const deleteOutlet = async (outletId) => {
    const response = await outletsAPI.delete(outletId);
    await fetchOutlets(); // Refresh list
    return response.data;
  };

  // Check if user is org-wide admin (can see all outlets)
  const isOrgWideAdmin = () => {
    // If user has access to all outlets in organization, they're org-wide admin
    // This is indicated by the backend not filtering outlets
    // For now, we'll use the admin role as a proxy
    return user?.role === 'admin';
  };

  const value = {
    outlets,
    currentOutlet,
    loading,
    selectOutlet,
    fetchOutlets,
    createOutlet,
    updateOutlet,
    deleteOutlet,
    isOrgWideAdmin
  };

  return (
    <OutletContext.Provider value={value}>
      {children}
    </OutletContext.Provider>
  );
}
