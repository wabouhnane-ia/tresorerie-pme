import { Link, useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Home,
  TrendingUp,
  Upload,
  FileText,
  Settings,
  Scale,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Tableau de bord", path: "/", icon: Home },
  { label: "Prévisions", path: "/forecasts", icon: TrendingUp },
  { label: "Téléchargements", path: "/uploads", icon: Upload },
  { label: "Rapports", path: "/reports", icon: FileText },
  { label: "Centre de décision", path: "/decision-center", icon: Scale },
  { label: "Paramètres", path: "/settings", icon: Settings },
];

export function AppSidebar({ subscription, onSubscriptionRefresh, isSuperAdmin }) {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const isExpired = !isSuperAdmin && !subscription?.is_access_allowed;

  const navItems = [
    ...NAV_ITEMS,
    ...(isSuperAdmin
      ? [{ label: "Gestion abonnements", path: "/admin/subscriptions", icon: null }]
      : []),
  ];

  const subscriptionBadgeVariant = isExpired ? "destructive" : "default";

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex flex-col gap-0.5 px-2 py-3">
          <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
            Tresorerie PME
          </span>
          <span className="text-xs text-muted-foreground">Gestion de trésorerie</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton
                    isActive={isActive(item.path)}
                    render={<Link to={item.path} />}
                  >
                    {item.icon && <item.icon className="h-4 w-4" />}
                    {item.label}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-2">
        {subscription && !isSuperAdmin && (
          <Card size="sm" className="shadow-none ring-0 bg-sidebar-accent/40">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-xs font-medium leading-snug">
                  {subscription?.plan?.name || "Tresorerie PME"}
                </CardTitle>
                <Badge variant={subscriptionBadgeVariant} className="shrink-0 text-[10px]">
                  {isExpired ? "Expiré" : "Actif"}
                </Badge>
              </div>
            </CardHeader>
            <CardFooter className="flex flex-col gap-2 pt-0">
              <Link to="/subscription" className="w-full">
                <Button variant="outline" size="sm" className="w-full">
                  Gérer
                </Button>
              </Link>
            </CardFooter>
          </Card>
        )}

        {isSuperAdmin && (
          <Card size="sm" className="shadow-none ring-0 bg-sidebar-accent/40">
            <CardContent className="pt-4">
              <p className="text-xs font-medium text-sidebar-foreground">
                Super Admin
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Accès illimité
              </p>
            </CardContent>
          </Card>
        )}
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}
