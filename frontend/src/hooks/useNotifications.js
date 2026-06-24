import { useEffect, useState, useCallback } from 'react';
import { notificationService } from '../services/notificationService';

/**
 * useNotifications Hook
 * Manages notification state and provides helper functions.
 */
export function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  const loadNotifications = useCallback(async () => {
    try {
      const result = await notificationService.getNotifications(20, 0);
      setNotifications(result.notifications || []);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const result = await notificationService.getStatistics();
      setStats(result);
      setUnreadCount(result.unread_notifications || 0);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }, []);

  const loadUnread = useCallback(async () => {
    try {
      const result = await notificationService.getUnreadNotifications();
      setUnreadCount(result.total || 0);
    } catch (error) {
      console.error('Failed to load unread:', error);
    }
  }, []);

  // Initial load and polling
  useEffect(() => {
    setLoading(true);
    Promise.all([loadNotifications(), loadStats()]).finally(() => setLoading(false));

    // Poll for new notifications every 30 seconds
    const pollInterval = setInterval(() => {
      loadUnread();
    }, 30000);

    return () => clearInterval(pollInterval);
  }, [loadNotifications, loadStats, loadUnread]);

  const markAsRead = useCallback(async (notificationId) => {
    try {
      await notificationService.markAsRead(notificationId);
      await loadStats();
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  }, [loadStats]);

  const markAllAsRead = useCallback(async () => {
    try {
      await notificationService.markAllAsRead();
      await loadStats();
      await loadNotifications();
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  }, [loadStats, loadNotifications]);

  const deleteNotification = useCallback(async (notificationId) => {
    try {
      await notificationService.deleteNotification(notificationId);
      await loadNotifications();
      await loadStats();
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  }, [loadNotifications, loadStats]);

  const getCriticalCount = useCallback(() => {
    return stats?.critical_notifications || 0;
  }, [stats]);

  const hasCritical = useCallback(() => {
    return (stats?.critical_notifications || 0) > 0;
  }, [stats]);

  const getNotificationsBySeverity = useCallback(
    (severity) => {
      return notifications.filter((n) => n.severity === severity);
    },
    [notifications]
  );

  const getNotificationsByType = useCallback(
    (type) => {
      return notifications.filter((n) => n.type === type);
    },
    [notifications]
  );

  return {
    // State
    notifications,
    stats,
    loading,
    unreadCount,

    // Actions
    markAsRead,
    markAllAsRead,
    deleteNotification,
    loadNotifications,
    loadStats,

    // Helpers
    getCriticalCount,
    hasCritical,
    getNotificationsBySeverity,
    getNotificationsByType,
  };
}
