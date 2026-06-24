import { useEffect, useState } from "react";
import API from "../services/api";
import { analyticsService } from "../services/analyticsService";
import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { useAuth } from "../hooks/useAuth";
import TreasuryMemoryCard from "../components/TreasuryMemoryCard";
import BusinessIntelligenceSection from "../components/BusinessIntelligenceSection";
import DecisionCenterSummary from "../components/DecisionCenterSummary";
import ForecastChart from "../components/ForecastChart";
import OnboardingStatusCard from "../components/OnboardingStatusCard";
import UpgradeBanner from "../components/UpgradeBanner";
import UploadZone from "../components/UploadZone";
import NotificationCenter from "../components/NotificationCenter";
import { useNotificationShell } from "../contexts/NotificationShellContext";
import { notificationService } from "../services/notificationService";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";

export default function DashboardPage() {
  const { user, createCompany } = useAuth();
  const [kpis, setKpis] = useState({});
  const [forecast, setForecast] = useState([]);
  const [businessIntelligence, setBusinessIntelligence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hasData, setHasData] = useState(false);
  const [analyzedAt, setAnalyzedAt] = useState(null);
  const [onboarding, setOnboarding] = useState(false);
  const [subscription, setSubscription] = useState(null);
  const [subscriptionLoading, setSubscriptionLoading] = useState(true); // <-- new
  const [upgrading, setUpgrading] = useState(false);
  const [error, setError] = useState(null);
  const [companyForm, setCompanyForm] = useState({ name: "", sector: "", city: "" });
  const [creatingCompany, setCreatingCompany] = useState(false);
  const [treasuryProfile, setTreasuryProfile] = useState(null);
  const { openCenter, openNotificationCenter, closeNotificationCenter } = useNotificationShell();

  useEffect(() => {
    fetchAllData();
  }, []);

  function formatDateTime(dateStr) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleString("fr-FR");
  }

  useEffect(() => {
    if (hasData || businessIntelligence) {
      fetchFromMongo();
    }
  }, [hasData, businessIntelligence]);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      await fetchSubscription();
      await fetchFromMongo();
      await fetchTreasuryProfile();
    } catch (err) {
      console.error(err);
      setError("Erreur lors du chargement des données");
    } finally {
      setLoading(false);
    }
  };

  const fetchTreasuryProfile = async () => {
    try {
      const res = await API.get("/upload/treasury-profile");
      setTreasuryProfile(res.data.profile);
    } catch (err) {
      console.error("Failed to fetch treasury profile:", err);
      setTreasuryProfile(null);
    }
  };

  const fetchSubscription = async () => {
    try {
      setSubscriptionLoading(true);
      setSubscription(await analyticsService.getSubscription());
    } catch (err) {
      console.warn("Could not fetch subscription:", err);
    } finally {
      setSubscriptionLoading(false);
    }
  };

  const fetchFromMongo = async () => {
    try {
      const latestRes = await API.get("/analytics/latest-analysis");

      if (latestRes.data.onboarding || !latestRes.data.has_real_data) {
        const onboardingInfo = safeGet(latestRes.data, "onboarding_info", {
          status: "NO_DATA",
          historical_months: 0,
          forecasting_enabled: false,
        });
        setHasData(false);
        setOnboarding(true);
        setKpis({ onboarding_info: onboardingInfo });
        return;
      }

      const kpisData = safeGet(latestRes.data, "kpis", {});
      const onboardingInfo = safeGet(latestRes.data, "onboarding_info", null);
      if (onboardingInfo) {
        kpisData.onboarding_info = onboardingInfo;
      }

      setHasData(true);
      setOnboarding(false);
      setKpis(kpisData);
      setForecast(ensureArray(safeGet(latestRes.data, "forecast", [])));
      setBusinessIntelligence(safeGet(latestRes.data, "business_intelligence", null));
      setAnalyzedAt(safeGet(latestRes.data, "analyzed_at", null));
    } catch (err) {
      console.error("Could not fetch latest analysis:", err);
      setHasData(false);
      setOnboarding(true);
    }
  };

  const handleUploadSuccess = async (uploadData) => {
    // Rely on the background upload pipeline to retrain forecasts.
    // The dashboard should only refresh data; do not trigger training here to avoid duplicates.
    await fetchAllData();
  };

  const handleUpgrade = async () => {
    setUpgrading(true);
    try {
      await API.post("/billing/upgrade");
      await fetchSubscription();
      await fetchAllData();
    } catch (err) {
      console.error("Upgrade failed:", err);
      await notificationService.createNotification({
        notification_type: "warning",
        severity: "high",
        title: "Mise à jour échouée",
        message: err?.message || String(err) || "La mise à jour a échoué",
      });
      openNotificationCenter();
    } finally {
      setUpgrading(false);
    }
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    if (!companyForm.name.trim()) return;
    setCreatingCompany(true);
    try {
      await createCompany(
        companyForm.name,
        companyForm.sector || "Services",
        companyForm.city || "Casablanca"
      );
      await fetchAllData();
    } catch (err) {
      console.error(err);
      await notificationService.createNotification({
        notification_type: "warning",
        severity: "high",
        title: "Échec de la création de l'entreprise",
        message: err?.message || String(err) || "Impossible de créer l'entreprise",
      });
      openNotificationCenter();
    } finally {
      setCreatingCompany(false);
    }
  };

  const isFreePlan =
    subscription?.plan?.code === "free_trial" ||
    subscription?.plan?.name?.toLowerCase().includes("free");
  const uploadLimitReached =
    isFreePlan &&
    subscription?.usage?.uploads_used >= (subscription?.plan?.max_uploads ?? 1);

  if (!user?.active_company_id) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
        <Card className="w-full max-w-lg border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-2xl font-semibold">
              Créer votre entreprise
            </CardTitle>
            <CardDescription>
              Commencez par créer votre compte
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateCompany} className="space-y-4">
              <div className="space-y-2">
                <Input
                  required
                  placeholder="Nom de l'entreprise"
                  value={companyForm.name}
                  onChange={(e) => setCompanyForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Input
                  placeholder="Secteur d'activité"
                  value={companyForm.sector}
                  onChange={(e) => setCompanyForm((f) => ({ ...f, sector: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Input
                  placeholder="Ville"
                  value={companyForm.city}
                  onChange={(e) => setCompanyForm((f) => ({ ...f, city: e.target.value }))}
                />
              </div>
              <Button
                type="submit"
                disabled={creatingCompany}
                className="w-full"
              >
                {creatingCompany ? "Création en cours..." : "Continuer"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (onboarding) {
    const onboardingInfo = safeGet(kpis, "onboarding_info", {
      status: "NO_DATA",
      historical_months: 0,
      forecasting_enabled: false,
    });

    return (
      <div className="mx-auto max-w-4xl space-y-8 py-8">
        {/* SECTION 1 — Titre */}
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">
            Commencez à utiliser l'outil
          </h1>
          <p className="text-sm text-muted-foreground">
            Importez vos données pour commencer
          </p>
        </div>

        {/* SECTION 2 — Onboarding Status */}
        <OnboardingStatusCard
          onboardingInfo={onboardingInfo}
          treasuryProfile={treasuryProfile}
        />

        {/* SECTION 3 — Upload Zone */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">
              Importer vos données
            </CardTitle>
            <CardDescription>
              Ajoutez votre historique de trésorerie
            </CardDescription>
          </CardHeader>
          <CardContent>
            <UploadZone
              onUploadSuccess={handleUploadSuccess}
              disabled={uploadLimitReached}
              disabledMessage="Limite d'imports gratuits atteinte"
              treasuryProfile={treasuryProfile}
            />
          </CardContent>
        </Card>

        {/* Features Grid */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold">
                Analyse financière
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Obtenez une analyse complète de votre santé financière
              </p>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold">
                Prévisions de trésorerie
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Projetez vos flux futurs pour anticiper les risques
              </p>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base font-semibold">
                Décisions stratégiques
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Recevez des recommandations pour optimiser votre trésorerie
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* SECTION 1 — Dashboard Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Tableau de bord
        </h1>
        <p className="text-sm text-muted-foreground">
          Vue d'ensemble de votre trésorerie
        </p>
        {hasData && analyzedAt && (
          <p className="text-xs text-muted-foreground">
            Analysé le {formatDateTime(analyzedAt)}
          </p>
        )}
      </div>

      {/* SECTION 2 — Upload / Onboarding Zone */}
      <Card className="border-border">
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg font-semibold">
                Importer des données
              </CardTitle>
              <CardDescription>
                Mettez à jour votre historique de trésorerie
              </CardDescription>
            </div>
            {subscription && (
              <div className="flex flex-wrap items-center gap-3">
                <Badge
                  variant={isFreePlan ? "secondary" : "default"}
                  className="text-xs"
                >
                  {subscription.plan?.name || "Essai gratuit"}
                </Badge>
                {isFreePlan && (
                  <span className="text-xs text-muted-foreground">
                    {subscription.usage?.uploads_used || 0} / {subscription.plan?.max_uploads || 1} import(s)
                  </span>
                )}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <UploadZone
            onUploadSuccess={handleUploadSuccess}
            disabled={uploadLimitReached}
            disabledMessage="Limite d'imports gratuits atteinte"
            treasuryProfile={treasuryProfile}
          />
        </CardContent>
      </Card>

      {!subscriptionLoading && subscription && (
        <UpgradeBanner
          show={!!subscription.show_upgrade_banner}
          onUpgrade={handleUpgrade}
          loading={upgrading}
        />
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription className="flex items-center justify-between">
            <div>
              <p className="font-medium">Erreur de chargement</p>
              <p className="text-sm">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAllData}
            >
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {loading && (
        <div className="py-8 text-center text-sm text-muted-foreground">
          Chargement des données...
        </div>
      )}

      {!loading && !onboarding && (
        <>
          <TreasuryMemoryCard profile={treasuryProfile} />
          {safeGet(kpis, "onboarding_info") && (
            <OnboardingStatusCard
              onboardingInfo={safeGet(kpis, "onboarding_info")}
              treasuryProfile={treasuryProfile}
            />
          )}

          {/* SECTION 3 — Business Intelligence */}
          <BusinessIntelligenceSection intelligence={businessIntelligence} />

          {/* SECTION 4 — Forecast */}
          {safeGet(kpis, "onboarding_info.forecasting_enabled", true) ? (
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg font-semibold">
                  Prévisions de trésorerie
                </CardTitle>
                <CardDescription>
                  Projection des flux futurs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ForecastChart data={forecast} treasuryBalance={safeGet(kpis, "treasury_balance")} />
              </CardContent>
            </Card>
          ) : (
            <Alert>
              <AlertDescription>
                <p className="font-medium">Prévisions désactivées</p>
                <p className="text-sm text-muted-foreground">
                  Activez les prévisions pour utiliser cette fonctionnalité
                </p>
              </AlertDescription>
            </Alert>
          )}

          {/* SECTION 5 — Decision Center Summary */}
          <DecisionCenterSummary />
        </>
      )}

      {/* Notification Center Dialog */}
      {openCenter && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="flex w-full max-w-4xl max-h-[90vh] flex-col overflow-hidden border-border shadow-lg">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-semibold">
                  Notifications
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={closeNotificationCenter}
                >
                  Fermer
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto p-0">
              <NotificationCenter />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
