import { createContext, useCallback, useContext, useMemo, useState, useEffect } from "react";
import { notificationService } from "@/services/notificationService";

const NotificationShellContext = createContext(null);

export function NotificationShellProvider({ children }) {
  const [openCenter, setOpenCenter] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [hasCritical, setHasCritical] = useState(false);
  const [loading, setLoading] = useState(false);

  const refreshUnreadCount = useCallback(async () => {
    try {
      setLoading(true);
      const result = await notificationService.getUnreadNotifications();
      setUnreadCount(result.total || 0);
      setHasCritical(result.has_critical || false);
    } catch (error) {
      console.error("Failed to refresh unread count:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const openNotificationCenter = useCallback(() => {
    setOpenCenter(true);
    refreshUnreadCount();
  }, [refreshUnreadCount]);

  const closeNotificationCenter = useCallback(() => {
    setOpenCenter(false);
  }, []);

  useEffect(() => {
    refreshUnreadCount();
    const interval = setInterval(refreshUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [refreshUnreadCount]);

  const value = useMemo(
    () => ({
      openCenter,
      setOpenCenter,
      openNotificationCenter,
      closeNotificationCenter,
      unreadCount,
      hasCritical,
      loading,
      refreshUnreadCount,
    }),
    [openCenter, openNotificationCenter, closeNotificationCenter, unreadCount, hasCritical, loading, refreshUnreadCount]
  );

  return (
    <NotificationShellContext.Provider value={value}>
      {children}
    </NotificationShellContext.Provider>
  );
}

export function useNotificationShell() {
  const context = useContext(NotificationShellContext);
  if (!context) {
    throw new Error("useNotificationShell must be used within NotificationShellProvider");
  }
  return context;
}
