import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL ?? '';

// Create axios instance with /api prefix
const axiosInstance = axios.create({
  baseURL: API_URL ? `${API_URL}/api` : '/api'
});

// Add request interceptor to include auth token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle auth errors
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
