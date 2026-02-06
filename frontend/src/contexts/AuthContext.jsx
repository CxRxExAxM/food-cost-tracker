import { createContext, useContext, useState, useEffect } from 'react';
import axios from '../lib/axios';

const API_URL = import.meta.env.VITE_API_URL ?? '';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');

    if (!token) {
      // Check if setup is required
      try {
        const response = await axios.get(`${API_URL}/auth/setup-status`);
        setSetupRequired(response.data.setup_required);
      } catch (error) {
        console.error('Error checking setup status:', error);
      }
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Auth check failed:', error);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      console.log('[AuthContext] Starting login...');
      const response = await axios.post(`${API_URL}/auth/login`, {
        email,
        password
      });

      console.log('[AuthContext] Login response:', response.data);
      const { access_token } = response.data;

      if (!access_token) {
        throw new Error('No access token received from server');
      }

      localStorage.setItem('token', access_token);
      console.log('[AuthContext] Token saved, fetching user info...');

      // Fetch user info
      const userResponse = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });

      console.log('[AuthContext] User info received:', userResponse.data);
      setUser(userResponse.data);
      setSetupRequired(false);
      return userResponse.data;
    } catch (error) {
      console.error('[AuthContext] Login failed:', error);
      throw error;
    }
  };

  const setup = async (email, username, password, fullName) => {
    try {
      console.log('[AuthContext] Starting setup...');
      const response = await axios.post(`${API_URL}/auth/setup`, {
        email,
        username,
        password,
        full_name: fullName
      });

      console.log('[AuthContext] Setup response:', response.data);
      const { access_token } = response.data;

      if (!access_token) {
        throw new Error('No access token received from server');
      }

      localStorage.setItem('token', access_token);
      console.log('[AuthContext] Token saved, fetching user info...');

      // Fetch user info
      const userResponse = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });

      console.log('[AuthContext] User info received:', userResponse.data);
      setUser(userResponse.data);
      setSetupRequired(false);
      return userResponse.data;
    } catch (error) {
      console.error('[AuthContext] Setup failed:', error);
      throw error;
    }
  };

  const setToken = async (token) => {
    try {
      console.log('[AuthContext] Setting new token...');
      localStorage.setItem('token', token);

      // Fetch user info with new token
      const userResponse = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      console.log('[AuthContext] User info received:', userResponse.data);
      setUser(userResponse.data);
      return userResponse.data;
    } catch (error) {
      console.error('[AuthContext] Failed to set token:', error);
      localStorage.removeItem('token');
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  // Helper to check roles
  const hasRole = (roles) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const isAdmin = () => hasRole(['admin']);
  const isChefOrAdmin = () => hasRole(['admin', 'chef']);

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      setupRequired,
      login,
      setup,
      setToken,
      logout,
      getAuthHeader,
      hasRole,
      isAdmin,
      isChefOrAdmin
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
