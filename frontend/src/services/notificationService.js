import API from './api';

export const notificationService = {
  /**
   * Get all notifications with pagination
   */
  async getNotifications(limit = 50, skip = 0, signal) {
    const response = await API.get(`/notifications`, {
      params: { limit, skip },
      withCredentials: true,
      signal,
    });
    return response.data;
  },

  /**
   * Get unread notifications (for notification bell)
   */
  async getUnreadNotifications() {
    const response = await API.get(`/notifications/unread`, {
      withCredentials: true,
    });
    return response.data;
  },

  /**
   * Get notification statistics
   */
  async getStatistics(signal) {
    const response = await API.get(`/notifications/statistics`, {
      withCredentials: true,
      signal,
    });
    return response.data;
  },

  /**
   * Mark a single notification as read
   */
  async markAsRead(notificationId) {
    const response = await API.patch(
      `/notifications/${notificationId}/read`,
      { is_read: true },
      { withCredentials: true }
    );
    return response.data;
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead() {
    const response = await API.patch(
      `/notifications/read-all`,
      {},
      { withCredentials: true }
    );
    return response.data;
  },

  /**
   * Delete a notification
   */
  async deleteNotification(notificationId) {
    const response = await API.delete(
      `/notifications/${notificationId}`,
      { withCredentials: true }
    );
    return response.data;
  },

  /**
   * Create a test notification via the server
   */
  async createNotification({ notification_type = 'warning', severity = 'high', title = '', message = '', metadata = {} } = {}) {
    const response = await API.post('/notifications', {
      notification_type,
      severity,
      title,
      message,
      metadata,
    });
    return response.data;
  },
};
