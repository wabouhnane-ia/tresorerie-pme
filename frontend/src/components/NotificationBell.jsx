import { Bell } from "lucide-react";
import { useTranslation } from "@/i18n/LanguageProvider";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useNotificationShell } from "@/contexts/NotificationShellContext";

export default function NotificationBell({ onClick }) {
  const { t } = useTranslation();
  const { unreadCount, hasCritical, loading, openNotificationCenter } = useNotificationShell();

  const handleClick = (e) => {
    if (onClick) onClick(e);
    else openNotificationCenter();
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      className="relative"
      onClick={handleClick}
      disabled={loading}
      aria-label={
        unreadCount > 0
          ? t("notifications.ariaUnread", { count: unreadCount })
          : t("notifications.ariaDefault")
      }
    >
      <Bell
        className={cn("h-4 w-4", hasCritical ? "text-destructive" : "text-muted-foreground")}
      />
      {unreadCount > 0 && (
        <Badge
          variant={hasCritical ? "destructive" : "default"}
          className="absolute -right-0.5 -top-0.5 h-4 min-w-4 px-1 text-[10px] font-semibold"
        >
          {unreadCount > 99 ? "99+" : unreadCount}
        </Badge>
      )}
    </Button>
  );
}
