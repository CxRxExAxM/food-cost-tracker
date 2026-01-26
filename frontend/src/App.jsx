import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { OutletProvider } from './contexts/OutletContext';
import Home from './pages/Home';
import Products from './pages/Products';
import Recipes from './pages/Recipes';
import Users from './pages/Users';
import Admin from './pages/Admin';
import Outlets from './pages/Outlets';
import Login from './pages/Login';
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
        path="/users"
        element={
          <ProtectedRoute>
            <Users />
          </ProtectedRoute>
        }
      />
      <Route
        path="/outlets"
        element={
          <ProtectedRoute>
            <Outlets />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <Admin />
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
      <Route
        path="/settings/vessels"
        element={
          <ProtectedRoute>
            <Vessels />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings/conversions"
        element={
          <ProtectedRoute>
            <BaseConversions />
          </ProtectedRoute>
        }
      />
      <Route
        path="/super-admin"
        element={
          <SuperAdminRoute>
            <SuperAdminDashboard />
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/organizations"
        element={
          <SuperAdminRoute>
            <SuperAdminOrganizations />
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/organizations/:orgId"
        element={
          <SuperAdminRoute>
            <SuperAdminOrganizationDetail />
          </SuperAdminRoute>
        }
      />
      <Route
        path="/super-admin/audit-logs"
        element={
          <SuperAdminRoute>
            <SuperAdminAuditLogs />
          </SuperAdminRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <OutletProvider>
          <div className="app">
            <ImpersonationBanner />
            <AppRoutes />
          </div>
        </OutletProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
