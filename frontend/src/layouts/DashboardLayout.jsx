import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Upload, Zap, BarChart4, FileText, BellRing, Settings, LogOut } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useNotificationShell } from '@/contexts/NotificationShellContext';
import NotificationBell from '@/components/NotificationBell';
import { ThemeToggle } from '@/components/ThemeToggle';
import { LanguageSelector } from '@/components/LanguageSelector';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useTranslation } from '@/i18n/LanguageProvider';

export default function DashboardLayout({ children }) {
  const navigate = useNavigate();
  const loc = useLocation();
  const { user, logout } = useAuth();
  const { openNotificationCenter } = useNotificationShell();
  const { t, dir } = useTranslation();

  const isActive = (path) => loc.pathname === path;

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: t('nav.dashboard') },
    { path: '/uploads', icon: Upload, label: t('nav.uploads') },
    { path: '/forecasts', icon: Zap, label: t('nav.forecasts') },
    { path: '/decision-center', icon: BarChart4, label: t('nav.decisionCenter') },
    { path: '/reports', icon: FileText, label: t('nav.reports') },
  ];

  const getInitials = () => {
    const first = user?.first_name?.[0] ?? "";
    const last = user?.last_name?.[0] ?? "";
    return (first + last).toUpperCase() || "U";
  };

  return (
    <div className="min-h-screen bg-background flex" dir={dir}>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:border-r lg:border-border lg:bg-sidebar">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <BarChart4 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight">{t('app.name')}</h2>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm transition-all duration-200 ease-out ${
                  isActive(item.path)
                    ? 'bg-primary/10 text-primary font-semibold border-l-2 border-primary'
                    : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                }`}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-sidebar-border mt-4">
          <button
            onClick={() => navigate('/settings')}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-all duration-200"
          >
            <Settings className="h-5 w-5" />
            {t('nav.settings')}
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="h-16 border-b border-border bg-card/60 backdrop-blur flex items-center justify-between px-4 lg:px-8 sticky top-0 z-30">
          <div className="flex items-center gap-3">
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <BarChart4 className="h-4 w-4 text-primary" />
              </div>
              <span className="font-semibold">{t('app.name')}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="hidden sm:flex items-center gap-2">
              <ThemeToggle />
              <LanguageSelector />
            </div>

            <NotificationBell onClick={openNotificationCenter} />

            <div className="flex items-center gap-3 ml-2">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium text-foreground">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
              <Avatar className="h-9 w-9 border border-border">
                <AvatarFallback className="text-sm font-semibold bg-primary/10 text-primary">
                  {getInitials()}
                </AvatarFallback>
              </Avatar>
              <button
                onClick={() => logout()}
                className="p-2 rounded-xl hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                title={t('common.logout')}
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Mobile Navigation (Tabs at bottom) */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border z-40 px-2 py-2">
          <div className="flex justify-around items-center">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-all duration-200 ${
                    isActive(item.path)
                      ? 'text-primary bg-primary/10'
                      : 'text-muted-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-[11px] font-medium">{item.label.split(' ')[0]}</span>
                </button>
              );
            })}
            <button
              onClick={() => navigate('/settings')}
              className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-all duration-200 ${
                loc.pathname === '/settings'
                  ? 'text-primary bg-primary/10'
                  : 'text-muted-foreground'
              }`}
            >
              <Settings className="h-5 w-5" />
              <span className="text-[11px] font-medium">{t('nav.settings')}</span>
            </button>
          </div>
        </div>

        {/* Content Area - Render children, not Outlet! */}
        <div className="flex-1 p-4 lg:p-8 pb-24 lg:pb-8">
          {children}
        </div>
      </main>
    </div>
  );
}
