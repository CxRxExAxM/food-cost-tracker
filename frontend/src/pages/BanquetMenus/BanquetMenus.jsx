import { useState, useEffect, useCallback, useRef } from 'react';
import axios from '../../lib/axios';
import Navigation from '../../components/Navigation';
import { useOutlet } from '../../contexts/OutletContext';
import MenuDashboard from './components/MenuDashboard';
import MenuItemList from './components/MenuItemList';
import NewMenuModal from './components/NewMenuModal';
import EditMenuModal from './components/EditMenuModal';
import ImportMenuModal from './components/ImportMenuModal';
import './BanquetMenus.css';

// localStorage keys for persisting selection
const STORAGE_KEYS = {
  mealPeriod: 'banquetMenus_mealPeriod',
  serviceType: 'banquetMenus_serviceType',
  menuId: 'banquetMenus_menuId',
  outletId: 'banquetMenus_outletId',
  guestCount: 'banquetMenus_guestCount',
  expandedItems: 'banquetMenus_expandedItems',
  menuMode: 'banquetMenus_menuMode'
};

// Helper to check if saved outlet matches current outlet
// Used by useState initializers to avoid loading stale data
const getSavedValueIfOutletMatches = (key, currentOutletId, parser = (v) => v) => {
  const savedOutletId = localStorage.getItem(STORAGE_KEYS.outletId);
  if (savedOutletId !== String(currentOutletId)) {
    return null; // Different outlet, don't restore
  }
  const saved = localStorage.getItem(key);
  return saved ? parser(saved) : null;
};

function BanquetMenus() {
  const { currentOutlet: selectedOutlet } = useOutlet();

  // Menu mode: 'banquet' or 'restaurant'
  const [menuMode, setMenuMode] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.menuMode) || 'banquet';
  });

  // Dropdown options
  const [mealPeriods, setMealPeriods] = useState([]);
  const [serviceTypes, setServiceTypes] = useState([]);
  const [menus, setMenus] = useState([]);

  // Selected values - only restore from localStorage if outlet matches
  const [selectedMealPeriod, setSelectedMealPeriod] = useState(() => {
    return getSavedValueIfOutletMatches(STORAGE_KEYS.mealPeriod, selectedOutlet?.id) || '';
  });
  const [selectedServiceType, setSelectedServiceType] = useState(() => {
    return getSavedValueIfOutletMatches(STORAGE_KEYS.serviceType, selectedOutlet?.id) || '';
  });
  const [selectedMenuId, setSelectedMenuId] = useState(() => {
    return getSavedValueIfOutletMatches(STORAGE_KEYS.menuId, selectedOutlet?.id, (v) => parseInt(v, 10));
  });

  // Track if selections have been validated against current outlet
  const selectionsValidatedRef = useRef(false);

  // Track if this is initial load to restore selections
  const isInitialLoadRef = useRef(true);

  // Current menu data
  const [currentMenu, setCurrentMenu] = useState(null);
  const [menuCost, setMenuCost] = useState(null);
  const [guestCount, setGuestCount] = useState(() => {
    return getSavedValueIfOutletMatches(STORAGE_KEYS.guestCount, selectedOutlet?.id, (v) => parseInt(v, 10)) || 0;
  });

  // Expanded menu items - only restore if outlet matches
  const [expandedItems, setExpandedItems] = useState(() => {
    try {
      const saved = getSavedValueIfOutletMatches(STORAGE_KEYS.expandedItems, selectedOutlet?.id, JSON.parse);
      return saved ? new Set(saved) : new Set();
    } catch {
      return new Set();
    }
  });

  // Ref for debounced cost refresh
  const costRefreshTimeoutRef = useRef(null);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (costRefreshTimeoutRef.current) {
        clearTimeout(costRefreshTimeoutRef.current);
      }
    };
  }, []);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showNewMenuModal, setShowNewMenuModal] = useState(false);
  const [showEditMenuModal, setShowEditMenuModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Save selections to localStorage when they change
  // Note: outletId is saved in the validation effect below, not here,
  // to avoid race conditions when switching outlets

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

  // Persist guest count
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.guestCount, String(guestCount));
  }, [guestCount]);

  // Persist expanded items
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.expandedItems, JSON.stringify([...expandedItems]));
  }, [expandedItems]);

  // Persist menu mode
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.menuMode, menuMode);
  }, [menuMode]);

  // Reset selections and fetch data when menu mode changes
  useEffect(() => {
    if (selectedOutlet?.id && selectedOutlet.id !== 'all') {
      // Reset cascade selections when mode changes
      setSelectedMealPeriod('');
      setSelectedServiceType('');
      setSelectedMenuId(null);
      setCurrentMenu(null);
      setMenuCost(null);
      setMenus([]);
      setServiceTypes([]);
      // Fetch meal periods for new mode
      fetchMealPeriods();
    }
  }, [menuMode]);

  // Validate and fetch when outlet becomes available
  useEffect(() => {
    if (selectedOutlet?.id) {
      const savedOutletId = localStorage.getItem(STORAGE_KEYS.outletId);
      const outletMatches = savedOutletId === String(selectedOutlet.id);

      // First time outlet loads - validate saved selections
      if (!selectionsValidatedRef.current) {
        selectionsValidatedRef.current = true;
        if (!outletMatches) {
          // Different outlet - clear saved selections from state AND localStorage
          setSelectedMealPeriod('');
          setSelectedServiceType('');
          setSelectedMenuId(null);
          setCurrentMenu(null);
          setMenuCost(null);
          setExpandedItems(new Set());
          localStorage.removeItem(STORAGE_KEYS.mealPeriod);
          localStorage.removeItem(STORAGE_KEYS.serviceType);
          localStorage.removeItem(STORAGE_KEYS.menuId);
          localStorage.removeItem(STORAGE_KEYS.guestCount);
          localStorage.removeItem(STORAGE_KEYS.expandedItems);
        }
        localStorage.setItem(STORAGE_KEYS.outletId, String(selectedOutlet.id));
      } else if (!outletMatches) {
        // User changed outlets - reset selections from state AND localStorage
        setSelectedMealPeriod('');
        setSelectedServiceType('');
        setSelectedMenuId(null);
        setCurrentMenu(null);
        setMenuCost(null);
        setExpandedItems(new Set());
        localStorage.removeItem(STORAGE_KEYS.mealPeriod);
        localStorage.removeItem(STORAGE_KEYS.serviceType);
        localStorage.removeItem(STORAGE_KEYS.menuId);
        localStorage.removeItem(STORAGE_KEYS.guestCount);
        localStorage.removeItem(STORAGE_KEYS.expandedItems);
        localStorage.setItem(STORAGE_KEYS.outletId, String(selectedOutlet.id));
      }

      fetchMealPeriods();

      // Mark initial load complete after a brief delay
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

  // Get outlet ID for API calls (null if 'all' selected)
  const getOutletIdParam = () => {
    if (!selectedOutlet || selectedOutlet.id === 'all') return null;
    return selectedOutlet.id;
  };

  const fetchMealPeriods = async () => {
    const outletId = getOutletIdParam();
    if (!outletId) {
      // No specific outlet selected - clear data
      setMealPeriods([]);
      return;
    }

    try {
      const response = await axios.get('/banquet-menus/meal-periods', {
        params: { outlet_id: outletId, menu_type: menuMode }
      });
      setMealPeriods(response.data.meal_periods || []);
    } catch (err) {
      console.error('Error fetching meal periods:', err);
      setMealPeriods([]);
    }
  };

  const fetchServiceTypes = async () => {
    const outletId = getOutletIdParam();
    if (!outletId) return;

    try {
      const response = await axios.get('/banquet-menus/service-types', {
        params: {
          outlet_id: outletId,
          meal_period: selectedMealPeriod,
          menu_type: menuMode
        }
      });
      setServiceTypes(response.data.service_types || []);
    } catch (err) {
      console.error('Error fetching service types:', err);
      setServiceTypes([]);
    }
  };

  const fetchMenus = async () => {
    const outletId = getOutletIdParam();
    if (!outletId) return;

    try {
      const response = await axios.get('/banquet-menus', {
        params: {
          outlet_id: outletId,
          meal_period: selectedMealPeriod,
          service_type: selectedServiceType,
          menu_type: menuMode
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

  const handleImportComplete = () => {
    // Refresh all the data after import
    fetchMealPeriods();
    // Reset selections to allow user to navigate to new menus
    setSelectedMealPeriod('');
    setSelectedServiceType('');
    setSelectedMenuId(null);
    setCurrentMenu(null);
    setMenuCost(null);
  };

  // Toggle expanded item
  const toggleExpandedItem = (itemId) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  // Debounced cost refresh for inline edits (doesn't refetch menu details)
  const debouncedCostRefresh = useCallback(() => {
    if (costRefreshTimeoutRef.current) {
      clearTimeout(costRefreshTimeoutRef.current);
    }
    costRefreshTimeoutRef.current = setTimeout(() => {
      if (selectedMenuId && guestCount > 0) {
        fetchMenuCost();
      }
    }, 800); // 800ms debounce
  }, [selectedMenuId, guestCount]);

  const handleGuestCountChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0) {
      setGuestCount(value);
    }
  };

  const handleMenuModeChange = (mode) => {
    if (mode !== menuMode) {
      setMenuMode(mode);
    }
  };

  if (!selectedOutlet?.id || selectedOutlet.id === 'all') {
    return (
      <div className="app-container">
        <Navigation />
        <main className="main-content">
          <div className="banquet-menus-page">
            <div className="page-header">
              <h1>Menus</h1>
            </div>
            <div className="empty-state">
              {selectedOutlet?.id === 'all'
                ? 'Please select a specific outlet to view menus. Menus are managed per outlet.'
                : 'Please select an outlet to view menus.'}
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
              <h1>Menus</h1>
              <p>Manage {menuMode === 'restaurant' ? 'restaurant' : 'banquet'} menu items and calculate food costs</p>
            </div>
            <div className="header-buttons">
              <button
                className="btn-import"
                onClick={() => setShowImportModal(true)}
              >
                Import CSV
              </button>
              <button
                className="btn-new-menu"
                onClick={() => setShowNewMenuModal(true)}
              >
                + New Menu
              </button>
            </div>
          </div>

          {/* Menu Type Toggle */}
          <div className="menu-type-toggle">
            <button
              className={`toggle-btn ${menuMode === 'banquet' ? 'active' : ''}`}
              onClick={() => handleMenuModeChange('banquet')}
            >
              Banquet
            </button>
            <button
              className={`toggle-btn ${menuMode === 'restaurant' ? 'active' : ''}`}
              onClick={() => handleMenuModeChange('restaurant')}
            >
              Restaurant
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
                menuType={menuMode}
              />

              {/* Menu Items */}
              <MenuItemList
                menuId={currentMenu.id}
                menuItems={currentMenu.menu_items || []}
                itemCosts={menuCost?.item_costs || []}
                guestCount={guestCount}
                expandedItems={expandedItems}
                onToggleExpand={toggleExpandedItem}
                onItemsChanged={handleMenuItemsChanged}
                onInlineEdit={debouncedCostRefresh}
                menuType={menuMode}
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
            menuType={menuMode}
          />
        )}

        {showEditMenuModal && currentMenu && (
          <EditMenuModal
            menu={currentMenu}
            onClose={() => setShowEditMenuModal(false)}
            onMenuUpdated={handleMenuUpdated}
            onMenuDeleted={handleMenuDeleted}
            menuType={menuMode}
          />
        )}

        {showImportModal && (
          <ImportMenuModal
            outletId={selectedOutlet.id}
            onClose={() => setShowImportModal(false)}
            onImportComplete={handleImportComplete}
          />
        )}
      </main>
    </div>
  );
}

export default BanquetMenus;
