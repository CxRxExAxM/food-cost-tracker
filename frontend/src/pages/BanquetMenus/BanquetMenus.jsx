import { useState, useEffect, useCallback, useRef } from 'react';
import axios from '../../lib/axios';
import Navigation from '../../components/Navigation';
import { useOutlet } from '../../contexts/OutletContext';
import MenuDashboard from './components/MenuDashboard';
import MenuItemList from './components/MenuItemList';
import NewMenuModal from './components/NewMenuModal';
import EditMenuModal from './components/EditMenuModal';
import './BanquetMenus.css';

// localStorage keys for persisting selection
const STORAGE_KEYS = {
  mealPeriod: 'banquetMenus_mealPeriod',
  serviceType: 'banquetMenus_serviceType',
  menuId: 'banquetMenus_menuId',
  outletId: 'banquetMenus_outletId'
};

function BanquetMenus() {
  const { currentOutlet: selectedOutlet } = useOutlet();

  // Dropdown options
  const [mealPeriods, setMealPeriods] = useState([]);
  const [serviceTypes, setServiceTypes] = useState([]);
  const [menus, setMenus] = useState([]);

  // Selected values - initialize from localStorage
  const [selectedMealPeriod, setSelectedMealPeriod] = useState(() => {
    const savedOutletId = localStorage.getItem(STORAGE_KEYS.outletId);
    if (savedOutletId === String(selectedOutlet?.id)) {
      return localStorage.getItem(STORAGE_KEYS.mealPeriod) || '';
    }
    return '';
  });
  const [selectedServiceType, setSelectedServiceType] = useState(() => {
    const savedOutletId = localStorage.getItem(STORAGE_KEYS.outletId);
    if (savedOutletId === String(selectedOutlet?.id)) {
      return localStorage.getItem(STORAGE_KEYS.serviceType) || '';
    }
    return '';
  });
  const [selectedMenuId, setSelectedMenuId] = useState(() => {
    const savedOutletId = localStorage.getItem(STORAGE_KEYS.outletId);
    if (savedOutletId === String(selectedOutlet?.id)) {
      const saved = localStorage.getItem(STORAGE_KEYS.menuId);
      return saved ? parseInt(saved, 10) : null;
    }
    return null;
  });

  // Track if this is initial load to restore selections
  const isInitialLoadRef = useRef(true);

  // Current menu data
  const [currentMenu, setCurrentMenu] = useState(null);
  const [menuCost, setMenuCost] = useState(null);
  const [guestCount, setGuestCount] = useState(0);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showNewMenuModal, setShowNewMenuModal] = useState(false);
  const [showEditMenuModal, setShowEditMenuModal] = useState(false);

  // Save selections to localStorage when they change
  useEffect(() => {
    if (selectedOutlet?.id) {
      localStorage.setItem(STORAGE_KEYS.outletId, String(selectedOutlet.id));
    }
  }, [selectedOutlet?.id]);

  useEffect(() => {
    if (selectedMealPeriod) {
      localStorage.setItem(STORAGE_KEYS.mealPeriod, selectedMealPeriod);
    }
  }, [selectedMealPeriod]);

  useEffect(() => {
    if (selectedServiceType) {
      localStorage.setItem(STORAGE_KEYS.serviceType, selectedServiceType);
    }
  }, [selectedServiceType]);

  useEffect(() => {
    if (selectedMenuId) {
      localStorage.setItem(STORAGE_KEYS.menuId, String(selectedMenuId));
    }
  }, [selectedMenuId]);

  // Fetch meal periods when outlet changes
  useEffect(() => {
    if (selectedOutlet?.id) {
      const savedOutletId = localStorage.getItem(STORAGE_KEYS.outletId);
      const outletChanged = savedOutletId !== String(selectedOutlet.id);

      fetchMealPeriods();

      // Only reset selections if outlet actually changed
      if (outletChanged && !isInitialLoadRef.current) {
        setSelectedMealPeriod('');
        setSelectedServiceType('');
        setSelectedMenuId(null);
        setCurrentMenu(null);
        setMenuCost(null);
        localStorage.setItem(STORAGE_KEYS.outletId, String(selectedOutlet.id));
      }
      // Mark initial load complete after a brief delay to allow cascades
      setTimeout(() => {
        isInitialLoadRef.current = false;
      }, 500);
    }
  }, [selectedOutlet?.id]);

  // Fetch service types when meal period changes
  useEffect(() => {
    if (selectedOutlet?.id && selectedMealPeriod) {
      fetchServiceTypes();
      // Only reset downstream if user changed the selection (not on initial restore)
      if (!isInitialLoadRef.current) {
        setSelectedServiceType('');
        setSelectedMenuId(null);
        setCurrentMenu(null);
        setMenuCost(null);
      }
    }
  }, [selectedMealPeriod]);

  // Fetch menus when service type changes
  useEffect(() => {
    if (selectedOutlet?.id && selectedMealPeriod && selectedServiceType) {
      fetchMenus();
      // Only reset if user changed the selection (not on initial restore)
      if (!isInitialLoadRef.current) {
        setSelectedMenuId(null);
        setCurrentMenu(null);
        setMenuCost(null);
      }
    }
  }, [selectedServiceType]);

  // Fetch menu details when menu is selected
  useEffect(() => {
    if (selectedMenuId) {
      fetchMenuDetails();
    }
  }, [selectedMenuId]);

  // Recalculate costs when guest count changes
  useEffect(() => {
    if (selectedMenuId && guestCount > 0) {
      fetchMenuCost();
    }
  }, [guestCount, selectedMenuId]);

  const fetchMealPeriods = async () => {
    // console.log('[BanquetMenus] fetchMealPeriods called for outlet:', selectedOutlet?.id);
    try {
      const response = await axios.get('/banquet-menus/meal-periods', {
        params: { outlet_id: selectedOutlet.id }
      });
      // console.log('[BanquetMenus] meal periods response:', response.data);
      setMealPeriods(response.data.meal_periods || []);
    } catch (err) {
      console.error('Error fetching meal periods:', err);
      setMealPeriods([]);
    }
  };

  const fetchServiceTypes = async () => {
    try {
      const response = await axios.get('/banquet-menus/service-types', {
        params: {
          outlet_id: selectedOutlet.id,
          meal_period: selectedMealPeriod
        }
      });
      setServiceTypes(response.data.service_types || []);
    } catch (err) {
      console.error('Error fetching service types:', err);
      setServiceTypes([]);
    }
  };

  const fetchMenus = async () => {
    try {
      const response = await axios.get('/banquet-menus', {
        params: {
          outlet_id: selectedOutlet.id,
          meal_period: selectedMealPeriod,
          service_type: selectedServiceType
        }
      });
      setMenus(response.data.menus || []);
    } catch (err) {
      console.error('Error fetching menus:', err);
      setMenus([]);
    }
  };

  const fetchMenuDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`/banquet-menus/${selectedMenuId}`);
      setCurrentMenu(response.data);
      // Also fetch cost data
      fetchMenuCost();
    } catch (err) {
      console.error('Error fetching menu details:', err);
      setError('Failed to load menu details');
      setCurrentMenu(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchMenuCost = async () => {
    if (!selectedMenuId || guestCount < 1) return;

    try {
      const response = await axios.get(`/banquet-menus/${selectedMenuId}/cost`, {
        params: { guests: guestCount }
      });
      setMenuCost(response.data);
    } catch (err) {
      console.error('Error fetching menu cost:', err);
    }
  };

  const handleMenuCreated = (newMenu) => {
    // Refresh the data
    fetchMealPeriods();
    setSelectedMealPeriod(newMenu.meal_period);
    setSelectedServiceType(newMenu.service_type);
    // Menu will be fetched via useEffect cascade
    setShowNewMenuModal(false);
  };

  const handleMenuUpdated = () => {
    fetchMenuDetails();
    fetchMenus();
    setShowEditMenuModal(false);
  };

  const handleMenuDeleted = () => {
    setSelectedMenuId(null);
    setCurrentMenu(null);
    setMenuCost(null);
    fetchMenus();
  };

  const handleMenuItemsChanged = () => {
    fetchMenuDetails();
  };

  const handleGuestCountChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0) {
      setGuestCount(value);
    }
  };

  if (!selectedOutlet?.id) {
    return (
      <div className="app-container">
        <Navigation />
        <main className="main-content">
          <div className="banquet-menus-page">
            <div className="page-header">
              <h1>Banquet Menus</h1>
            </div>
            <div className="empty-state">
              Please select an outlet to view banquet menus.
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-container">
      <Navigation />
      <main className="main-content">
        <div className="banquet-menus-page">
          <div className="page-header">
            <div className="header-content">
              <h1>Banquet Menus</h1>
              <p>Manage banquet menu items and calculate food costs</p>
            </div>
            <button
              className="btn-new-menu"
              onClick={() => setShowNewMenuModal(true)}
            >
              + New Menu
            </button>
          </div>

          {/* Cascading Dropdowns */}
          <div className="menu-selectors">
            <div className="selector-group">
              <label>Meal Period</label>
              <select
                value={selectedMealPeriod}
                onChange={(e) => setSelectedMealPeriod(e.target.value)}
                className="selector-dropdown"
              >
                <option value="">Select Meal Period</option>
                {mealPeriods.map((period) => (
                  <option key={period} value={period}>
                    {period}
                  </option>
                ))}
              </select>
            </div>

            <div className="selector-group">
              <label>Service Type</label>
              <select
                value={selectedServiceType}
                onChange={(e) => setSelectedServiceType(e.target.value)}
                className="selector-dropdown"
                disabled={!selectedMealPeriod}
              >
                <option value="">Select Service Type</option>
                {serviceTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div className="selector-group selector-group-wide">
              <label>Menu Name</label>
              <select
                value={selectedMenuId || ''}
                onChange={(e) => setSelectedMenuId(e.target.value ? parseInt(e.target.value, 10) : null)}
                className="selector-dropdown"
                disabled={!selectedServiceType}
              >
                <option value="">Select Menu</option>
                {menus.map((menu) => (
                  <option key={menu.id} value={menu.id}>
                    {menu.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          {loading && (
            <div className="loading">
              <div className="loading-spinner-enhanced"></div>
              <span>Loading menu...</span>
            </div>
          )}

          {!loading && currentMenu && (
            <>
              {/* Dashboard */}
              <MenuDashboard
                menu={currentMenu}
                menuCost={menuCost}
                guestCount={guestCount}
                onGuestCountChange={handleGuestCountChange}
                onEditClick={() => setShowEditMenuModal(true)}
              />

              {/* Menu Items */}
              <MenuItemList
                menuId={currentMenu.id}
                menuItems={currentMenu.menu_items || []}
                itemCosts={menuCost?.item_costs || []}
                guestCount={guestCount}
                onItemsChanged={handleMenuItemsChanged}
              />
            </>
          )}

          {!loading && !currentMenu && selectedServiceType && menus.length === 0 && (
            <div className="empty-state">
              No menus found for this selection. Create a new menu to get started.
            </div>
          )}

          {!loading && !currentMenu && !selectedMealPeriod && mealPeriods.length === 0 && (
            <div className="empty-state">
              No menus exist for this outlet yet. Create a new menu to get started.
            </div>
          )}

          {!loading && !currentMenu && selectedMealPeriod && !selectedServiceType && (
            <div className="empty-state-hint">
              Select a service type to continue.
            </div>
          )}

          {!loading && !currentMenu && selectedServiceType && menus.length > 0 && !selectedMenuId && (
            <div className="empty-state-hint">
              Select a menu to view details.
            </div>
          )}
        </div>

        {/* Modals */}
        {showNewMenuModal && (
          <NewMenuModal
            outletId={selectedOutlet.id}
            onClose={() => setShowNewMenuModal(false)}
            onMenuCreated={handleMenuCreated}
          />
        )}

        {showEditMenuModal && currentMenu && (
          <EditMenuModal
            menu={currentMenu}
            onClose={() => setShowEditMenuModal(false)}
            onMenuUpdated={handleMenuUpdated}
            onMenuDeleted={handleMenuDeleted}
          />
        )}
      </main>
    </div>
  );
}

export default BanquetMenus;
