import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OutletProvider } from './contexts/OutletContext';
import { ToastProvider } from './contexts/ToastContext';
import Home from './pages/Home';
import Products from './pages/Products';
import Recipes from './pages/Recipes';
import Users from './pages/Users';
import Admin from './pages/Admin';
import Outlets from './pages/Outlets';
import Login from './pages/Login';
import Settings from './pages/Settings/Settings';
import SuperAdminDashboard from './pages/SuperAdmin/Dashboard';
import SuperAdminOrganizations from './pages/SuperAdmin/Organizations';
import SuperAdminOrganizationDetail from './pages/SuperAdmin/OrganizationDetail';
import SuperAdminAuditLogs from './pages/SuperAdmin/AuditLogs';
import BanquetMenus from './pages/BanquetMenus/BanquetMenus';
import Vessels from './pages/Settings/Vessels';
import BaseConversions from './pages/Settings/BaseConversions';
import ImpersonationBanner from './components/ImpersonationBanner';
import './App.css';

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { user, loading, setupRequired } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (setupRequired) {
    return <Navigate to="/login" replace />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// Public route - redirect to home if already logged in
function PublicRoute({ children }) {
  const { user, loading, setupRequired } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // Allow access to login for setup
  if (setupRequired) {
    return children;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Admin route - requires admin access
function AdminRoute({ children }) {
  const { user, loading, isAdmin } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin()) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Super Admin route - requires super admin access
function SuperAdminRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_super_admin) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={
          <ProtectedRoute>
            <Products />
          </ProtectedRoute>
        }
      />
      <Route
        path="/recipes"
        element={
          <ProtectedRoute>
            <Recipes />
          </ProtectedRoute>
        }
      />
      <Route
        path="/banquet-menus"
        element={
          <ProtectedRoute>
            <BanquetMenus />
          </ProtectedRoute>
        }
      />

      {/* Settings - nested routes */}
      <Route
        path="/settings"
        element={
          <AdminRoute>
            <Settings />
          </AdminRoute>
        }
      >
        <Route path="users" element={<Users embedded />} />
        <Route path="outlets" element={<Outlets embedded />} />
        <Route path="vessels" element={<Vessels embedded />} />
        <Route path="conversions" element={<BaseConversions embedded />} />
        <Route path="admin" element={<Admin embedded />} />
        {/* Super Admin nested routes */}
        <Route path="super-admin" element={<SuperAdminDashboard />} />
        <Route path="super-admin/organizations" element={<SuperAdminOrganizations />} />
        <Route path="super-admin/organizations/:orgId" element={<SuperAdminOrganizationDetail />} />
        <Route path="super-admin/audit-logs" element={<SuperAdminAuditLogs />} />
      </Route>

      {/* Legacy routes - redirect to new settings paths */}
      <Route path="/users" element={<Navigate to="/settings/users" replace />} />
      <Route path="/outlets" element={<Navigate to="/settings/outlets" replace />} />
      <Route path="/admin" element={<Navigate to="/settings/admin" replace />} />
      <Route path="/super-admin" element={<Navigate to="/settings/super-admin" replace />} />
      <Route path="/super-admin/*" element={<Navigate to="/settings/super-admin" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <OutletProvider>
            <div className="app">
              <ImpersonationBanner />
              <AppRoutes />
            </div>
          </OutletProvider>
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
