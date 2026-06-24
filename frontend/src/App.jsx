import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { ThemeProvider } from "./hooks/useTheme";
import { LanguageProvider } from "./i18n/LanguageProvider";
import { NotificationShellProvider } from "./contexts/NotificationShellContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import UploadsPage from "./pages/UploadsPage";
import ReportsPage from "./pages/ReportsPage";
import AdminSubscriptionsPage from "./pages/AdminSubscriptionsPage";
import SubscriptionPage from "./pages/SubscriptionPage";
import ForecastPage from "./pages/ForecastPage";
import DecisionCenterPage from "./pages/DecisionCenterPage";
import NotificationCenter from "./components/NotificationCenter";
import NotificationPanel from "./components/NotificationPanel";
import SettingsPage from "./pages/SettingsPage";
import DashboardLayout from "./layouts/DashboardLayout";
import "./index.css";

// Loading fallback
function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

// Protected Route wrapper
function ProtectedRoute({ children }) {
  const { isAuth, loading } = useAuth();

  if (loading) {
    return <PageLoader />;
  }

  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }

  return <DashboardLayout>{children}</DashboardLayout>;
}

// Admin Route wrapper
function AdminRoute({ children }) {
  const { isAuth, loading, user } = useAuth();

  if (loading) {
    return <PageLoader />;
  }

  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== "super_admin") {
    return <Navigate to="/" replace />;
  }

  return <DashboardLayout>{children}</DashboardLayout>;
}

// Routes configuration
function AppContent() {
  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<LoginPage />} />

          {/* Protected routes */}
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/forecasts" element={<ProtectedRoute><ForecastPage /></ProtectedRoute>} />
          <Route path="/uploads" element={<ProtectedRoute><UploadsPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/subscription" element={<ProtectedRoute><SubscriptionPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/decision-center" element={<ProtectedRoute><DecisionCenterPage /></ProtectedRoute>} />
          <Route path="/notifications" element={<ProtectedRoute><NotificationCenter /></ProtectedRoute>} />
          <Route path="/notifications-panel" element={<ProtectedRoute><NotificationPanel /></ProtectedRoute>} />

          {/* Admin routes */}
          <Route path="/admin/subscriptions" element={<AdminRoute><AdminSubscriptionsPage /></AdminRoute>} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <LanguageProvider>
        <ThemeProvider>
          <AuthProvider>
            <NotificationShellProvider>
              <AppContent />
            </NotificationShellProvider>
          </AuthProvider>
        </ThemeProvider>
      </LanguageProvider>
    </ErrorBoundary>
  );
}
