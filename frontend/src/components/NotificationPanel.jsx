import { useEffect, useState } from 'react';
import { notificationService } from '../services/notificationService';
import { useTranslation } from '../i18n/LanguageProvider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import { Skeleton } from './ui/skeleton';
import { AlertTriangle, ShieldAlert, CircleCheck, TrendingUp } from 'lucide-react';

/**
 * NotificationPanel
 * Compact notification panel for dashboard - shows latest 5 notifications
 */
function NotificationPanel({ onOpenFullCenter }) {
  const { formatDate, t } = useTranslation();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadNotifications = async () => {
      try {
        const result = await notificationService.getNotifications(5, 0);
        setNotifications(result.notifications || []);
      } catch (error) {
        console.error('Failed to load notifications:', error);
      } finally {
        setLoading(false);
      }
    };

    loadNotifications();

    // Refresh every 60 seconds
    const interval = setInterval(loadNotifications, 60000);
    return () => clearInterval(interval);
  }, [t]);

  const getSeverityVariant = (severity) => {
    if (severity === 'critical') return 'destructive';
    if (severity === 'high') return 'default';
    if (severity === 'medium') return 'secondary';
    return 'outline';
  };

  const getSeverityLabel = (severity) => {
    const key = `api.severity.${severity}`;
    return t(key, severity.charAt(0).toUpperCase() + severity.slice(1));
  };

  const getSeverityIcon = (severity) => {
    if (severity === 'critical' || severity === 'high') return <AlertTriangle className="h-4 w-4" />;
    if (severity === 'medium') return <ShieldAlert className="h-4 w-4" />;
    if (severity === 'low') return <CircleCheck className="h-4 w-4" />;
    return <TrendingUp className="h-4 w-4" />;
  };

  if (loading) {
    return (
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-base">{t("notifications.latest")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (notifications.length === 0) {
    return (
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-base">{t("notifications.latest")}</CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center">
          <p className="text-sm text-muted-foreground">{t("notifications.none")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t("notifications.latest")}</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onOpenFullCenter}
            className="text-xs"
          >
            {t("notifications.viewAll")}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 px-0">
        {notifications.slice(0, 5).map((notification, index) => (
          <div key={notification.id}>
            {index > 0 && <Separator />}
            <div className="px-6 py-3 hover:bg-muted/50 transition-colors cursor-pointer">
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 shrink-0 ${
                  notification.severity === 'critical' ? 'text-destructive' : 
                  notification.severity === 'high' ? 'text-primary' : 'text-muted-foreground'
                }`}>
                  {getSeverityIcon(notification.severity)}
                </div>
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-foreground line-clamp-1">
                      {notification.title}
                    </p>
                    <Badge
                      variant={getSeverityVariant(notification.severity)}
                      className="text-xs shrink-0"
                    >
                      {getSeverityLabel(notification.severity)}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {notification.message}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(notification.created_at, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
                {!notification.is_read && (
                  <div className="w-2 h-2 rounded-full bg-primary shrink-0 mt-2" />
                )}
              </div>
            </div>
          </div>
        ))}
      </CardContent>

      <Separator />
      <div className="p-3 bg-muted/30">
        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenFullCenter}
          className="w-full text-xs"
        >
          {t("notifications.openCenter")}
        </Button>
      </div>
    </Card>
  );
}

export default NotificationPanel;
