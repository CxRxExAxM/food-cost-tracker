import api from './client';

/**
 * Outlet API Service
 * Provides methods for managing outlets, user assignments, and statistics
 */
export const outletsAPI = {
  /**
   * Get list of all outlets (filtered by user's access)
   * @returns {Promise} Array of outlets
   */
  list: () => api.get('/outlets'),

  /**
   * Get outlet details by ID
   * @param {number} outletId - Outlet ID
   * @returns {Promise} Outlet object
   */
  get: (outletId) => api.get(`/outlets/${outletId}`),

  /**
   * Get organization statistics (products, recipes, users, outlets, imports)
   * @returns {Promise} Statistics object
   */
  getOrganizationStats: () => api.get('/outlets/organization/stats'),

  /**
   * Get outlet statistics (products count, recipes count, users count)
   * @param {number} outletId - Outlet ID
   * @returns {Promise} Statistics object
   */
  getStats: (outletId) => api.get(`/outlets/${outletId}/stats`),

  /**
   * Create new outlet (admin only)
   * @param {object} data - Outlet data { name, location, description }
   * @returns {Promise} Created outlet
   */
  create: (data) => api.post('/outlets', data),

  /**
   * Update outlet details (admin only)
   * @param {number} outletId - Outlet ID
   * @param {object} data - Fields to update
   * @returns {Promise} Updated outlet
   */
  update: (outletId, data) => api.patch(`/outlets/${outletId}`, data),

  /**
   * Delete/deactivate outlet (admin only)
   * @param {number} outletId - Outlet ID
   * @returns {Promise} Success message
   */
  delete: (outletId) => api.delete(`/outlets/${outletId}`),

  /**
   * Get list of users assigned to outlet
   * @param {number} outletId - Outlet ID
   * @returns {Promise} Array of users
   */
  getUsers: (outletId) => api.get(`/outlets/${outletId}/users`),

  /**
   * Assign user to outlet (admin only)
   * @param {number} outletId - Outlet ID
   * @param {number} userId - User ID
   * @returns {Promise} Success message
   */
  assignUser: (outletId, userId) =>
    api.post(`/outlets/${outletId}/users/${userId}`),

  /**
   * Remove user from outlet (admin only)
   * @param {number} outletId - Outlet ID
   * @param {number} userId - User ID
   * @returns {Promise} Success message
   */
  removeUser: (outletId, userId) =>
    api.delete(`/outlets/${outletId}/users/${userId}`)
};
