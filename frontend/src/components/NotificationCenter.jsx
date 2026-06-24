import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { notificationService } from "@/services/notificationService";
import { useTranslation } from "@/i18n/LanguageProvider";
import { useNotificationShell } from "@/contexts/NotificationShellContext";
import { formatDate } from "@/utils/dateUtils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, ShieldAlert, CircleCheck, TrendingUp, Loader2 } from "lucide-react";

const NotificationCard = React.memo(({ 
  notification, 
  handleMarkAsRead, 
  handleDelete, 
  markingAsRead, 
  deleting, 
  t, 
  formatDate 
}) => {
  const getSeverityVariant = useCallback((severity) => {
    if (severity === 'critical') return 'destructive';
    if (severity === 'high') return 'default';
    if (severity === 'medium') return 'secondary';
    return 'outline';
  }, []);

  const getSeverityLabel = useCallback((severity) => {
    const key = `api.severity.${severity}`;
    return t(key, severity.charAt(0).toUpperCase() + severity.slice(1));
  }, [t]);

  const getSeverityIcon = useCallback((severity) => {
    if (severity === 'critical' || severity === 'high') return <AlertTriangle className="h-4 w-4" />;
    if (severity === 'medium') return <ShieldAlert className="h-4 w-4" />;
    if (severity === 'low') return <CircleCheck className="h-4 w-4" />;
    return <TrendingUp className="h-4 w-4" />;
  }, []);

  const isMarkingAsRead = markingAsRead.has(notification.id);
  const isDeleting = deleting.has(notification.id);

  return (
    <Card className={`${!notification.is_read ? 'border-l-4 border-l-primary' : ''} border-border`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <div className={`mt-0.5 shrink-0 ${
                notification.severity === 'critical' ? 'text-destructive' : 
                notification.severity === 'high' ? 'text-primary' : 'text-muted-foreground'
              }`}>
                {getSeverityIcon(notification.severity)}
              </div>
              <Badge variant={getSeverityVariant(notification.severity)} className="text-xs">
                {getSeverityLabel(notification.severity)}
              </Badge>
              {!notification.is_read && (
                <Badge variant="outline" className="text-xs">
                  {t("notifications.notRead")}
                </Badge>
              )}
            </div>
            <CardTitle className="text-base leading-snug">{notification.title}</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => handleDelete(notification.id)}
            className="shrink-0"
            disabled={isDeleting || isMarkingAsRead}
          >
            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <span>×</span>}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <CardDescription className="text-sm">{notification.message}</CardDescription>
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {formatDate(notification.created_at, {
              dateStyle: "medium",
              timeStyle: "short",
            })}
          </p>
          {!notification.is_read && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleMarkAsRead(notification.id)}
              className="text-xs"
              disabled={isDeleting || isMarkingAsRead}
            >
              {isMarkingAsRead ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
              {t("notifications.markAsRead")}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
NotificationCard.displayName = "NotificationCard";

export default function NotificationCenter() {
  const { formatDate: i18nFormatDate, t } = useTranslation();
  const { refreshUnreadCount } = useNotificationShell();
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [markingAsRead, setMarkingAsRead] = useState(new Set());
  const [deleting, setDeleting] = useState(new Set());
  const limit = 50;

  const loadNotifications = useCallback(async (signal) => {
    try {
      setLoading(true);
      const result = await notificationService.getNotifications(limit, page * limit, signal);
      setNotifications(result.notifications || []);
      setTotal(result.total || 0);
    } catch (error) {
      if (axios.isCancel(error) || error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load notifications:', error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  const loadStats = useCallback(async (signal) => {
    try {
      const result = await notificationService.getStatistics(signal);
      setStats(result);
    } catch (error) {
      if (axios.isCancel(error) || error.name === 'AbortError') {
        return;
      }
      console.error('Failed to load notification stats:', error);
    }
  }, []);

  const handleMarkAsRead = useCallback(async (notificationId) => {
    try {
      setMarkingAsRead(prev => {
        const newSet = new Set(prev);
        newSet.add(notificationId);
        return newSet;
      });
      await notificationService.markAsRead(notificationId);
      await refreshUnreadCount();
      await loadNotifications();
      await loadStats();
    } catch (error) {
      console.error('Failed to mark as read:', error);
    } finally {
      setMarkingAsRead(prev => {
        const newSet = new Set(prev);
        newSet.delete(notificationId);
        return newSet;
      });
    }
  }, [refreshUnreadCount, loadNotifications, loadStats]);

  const handleMarkAllAsRead = useCallback(async () => {
    try {
      await notificationService.markAllAsRead();
      await refreshUnreadCount();
      await loadNotifications();
      await loadStats();
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  }, [refreshUnreadCount, loadNotifications, loadStats]);

  const handleDelete = useCallback(async (notificationId) => {
    try {
      setDeleting(prev => {
        const newSet = new Set(prev);
        newSet.add(notificationId);
        return newSet;
      });
      await notificationService.deleteNotification(notificationId);
      await refreshUnreadCount();
      await loadNotifications();
      await loadStats();
    } catch (error) {
      console.error('Failed to delete notification:', error);
    } finally {
      setDeleting(prev => {
        const newSet = new Set(prev);
        newSet.delete(notificationId);
        return newSet;
      });
    }
  }, [refreshUnreadCount, loadNotifications, loadStats]);

  const filteredNotifications = useMemo(() => {
    return notifications.filter((n) => {
      if (filter === 'unread') return !n.is_read;
      if (filter === 'critical') return n.severity === 'critical';
      return true;
    });
  }, [notifications, filter]);

  const hasNextPage = useMemo(() => {
    return (page + 1) * limit < total;
  }, [page, total]);

  useEffect(() => {
    const controller = new AbortController();
    loadNotifications(controller.signal);
    loadStats(controller.signal);
    return () => controller.abort();
  }, [page, filter, loadNotifications, loadStats]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-2xl">{t("notifications.center")}</CardTitle>
          <CardDescription>{t("notifications.manageAlerts")}</CardDescription>
        </CardHeader>
        {stats && (
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs">Total</CardDescription>
                  <CardTitle className="text-2xl">{stats.total_notifications}</CardTitle>
                </CardHeader>
              </Card>
              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs">{t("notifications.unread")}</CardDescription>
                  <CardTitle className="text-2xl">{stats.unread_notifications}</CardTitle>
                </CardHeader>
              </Card>
              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs">{t("notifications.critical")}</CardDescription>
                  <CardTitle className="text-2xl text-destructive">
                    {stats.critical_notifications}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs">{t("notifications.success")}</CardDescription>
                  <CardTitle className="text-2xl text-primary">
                    {stats.by_type?.success || 0}
                  </CardTitle>
                </CardHeader>
              </Card>
            </div>
          </CardContent>
        )}
      </Card>

      <Card className="border-border">
        <Tabs value={filter} onValueChange={(value) => { setFilter(value); setPage(0); }}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="all">{t("notifications.all")}</TabsTrigger>
                <TabsTrigger value="unread">{t("notifications.unread")}</TabsTrigger>
                <TabsTrigger value="critical">{t("notifications.critical")}</TabsTrigger>
              </TabsList>
              {stats && stats.unread_notifications > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleMarkAllAsRead}
                  className="text-xs"
                >
                  {t("notifications.markAllAsRead")}
                </Button>
              )}
            </div>
          </CardHeader>

          <Separator />

          <CardContent className="pt-6">
            <TabsContent value={filter} className="mt-0">
              {loading && (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <Card key={i} className="border-border">
                      <CardHeader>
                        <Skeleton className="h-4 w-1/4 mb-2" />
                        <Skeleton className="h-5 w-3/4" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-4 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {!loading && filteredNotifications.length === 0 && (
                <Card className="border-dashed border-border">
                  <CardContent className="py-12 text-center">
                    <p className="text-sm text-muted-foreground">{t("notifications.none")}</p>
                  </CardContent>
                </Card>
              )}

              {!loading && filteredNotifications.length > 0 && (
                <ScrollArea className="h-[600px] pr-4">
                  <div className="space-y-4">
                    {filteredNotifications.map((notification) => (
                      <NotificationCard
                        key={notification.id}
                        notification={notification}
                        handleMarkAsRead={handleMarkAsRead}
                        handleDelete={handleDelete}
                        markingAsRead={markingAsRead}
                        deleting={deleting}
                        t={t}
                        formatDate={i18nFormatDate}
                      />
                    ))}
                  </div>
                </ScrollArea>
              )}

              {!loading && filteredNotifications.length > 0 && (
                <div className="flex items-center justify-center gap-2 mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                  >
                    ← {t("notifications.previous")}
                  </Button>
                  <span className="text-sm text-muted-foreground px-4">
                    {t("notifications.page", { page: page + 1 })}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page + 1)}
                    disabled={!hasNextPage}
                  >
                    {t("notifications.next")} →
                  </Button>
                </div>
              )}
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>
    </div>
  );
}
