import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { subscriptionService } from "../services/subscriptionService";
import { useTranslation } from "../i18n/LanguageProvider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button, buttonVariants } from "../components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "../components/ui/alert";
import { Skeleton } from "../components/ui/skeleton";
import { Separator } from "../components/ui/separator";
import { cn } from "../lib/utils";
import { Check, Zap, TrendingUp, Shield, FileText, Calendar, Upload, Clock, Database, ShieldCheck } from "lucide-react";
import API from "../services/api";

const STATUS_VARIANTS = {
  trial: "secondary",
  active: "default",
  expired: "destructive",
  cancelled: "outline",
};

const DEFAULT_FEATURES = [
  "upload_intelligent",
  "memoire_historique",
  "previsions",
  "business_intelligence",
  "decision_center",
  "notifications",
  "executive_pdf"
];

const featureIcons = {
  upload_intelligent: Zap,
  memoire_historique: FileText,
  previsions: TrendingUp,
  business_intelligence: TrendingUp,
  decision_center: Check,
  notifications: Shield,
  executive_pdf: FileText,
};

export default function SubscriptionPage() {
  const { formatDate, t } = useTranslation();
  const [subscription, setSubscription] = useState(null);
  const [treasuryProfile, setTreasuryProfile] = useState(null);
  const [uploads, setUploads] = useState([]);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [subData, profileData, uploadList, latestAnalysis] = await Promise.all([
        subscriptionService.getSubscription(),
        API.get("/upload/treasury-profile").catch(() => ({ data: { profile: null } })),
        API.get("/upload/list").catch(() => ({ data: [] })),
        API.get("/analytics/latest-analysis").catch(() => ({ data: null })),
      ]);
      setSubscription(subData);
      setTreasuryProfile(profileData?.data?.profile);
      setUploads(uploadList?.data || []);
      setAnalyticsData(latestAnalysis?.data);
    } catch (err) {
      console.error(err);
      setError(t("subscriptionPage.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const handleActivate = async () => {
    setActionLoading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await subscriptionService.activate();
      setSubscription(res.subscription);
      setMessage(t("subscriptionPage.activated"));
    } catch (err) {
      console.error(err);
      setError(t("subscriptionPage.activateError"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm(t("subscriptionPage.cancelConfirm"))) return;
    setActionLoading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await subscriptionService.cancel();
      setSubscription(res.subscription);
      setMessage(t("subscriptionPage.cancelled"));
    } catch (err) {
      console.error(err);
      setError(t("subscriptionPage.cancelError"));
    } finally {
      setActionLoading(false);
    }
  };

  const status = subscription?.status || "trial";
  const canActivate = status === "trial" || status === "expired" || status === "cancelled";
  const canCancel = status === "active" || status === "trial";
  const features = subscription?.features?.length > 0 ? subscription.features : DEFAULT_FEATURES;

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-8 space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Card className="border-border">
          <CardContent className="pt-6 space-y-6">
            <Skeleton className="h-40 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-8 space-y-2">
        <h1 className="text-3xl font-bold text-foreground">{t("subscriptionPage.title")}</h1>
        <p className="text-muted-foreground">{t("subscriptionPage.subtitle")}</p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>{t("common.error")}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {message && (
        <Alert className="mb-6">
          <AlertTitle>{t("common.success")}</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        {/* Hero Card */}
        <Card className="border-border overflow-hidden">
          <CardHeader className="bg-muted/30">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <CardDescription className="text-xs uppercase tracking-wider">
                  {t("subscription.yourPlan")}
                </CardDescription>
                <CardTitle className="text-2xl">
                  {subscription?.plan_name || "Plan Premium"}
                </CardTitle>
              </div>
              <Badge variant={STATUS_VARIANTS[status] || STATUS_VARIANTS.trial}>
                {t(`subscriptionPage.status.${status}`)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid sm:grid-cols-2 gap-6 mb-6">
              {/* Statut */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  Statut
                </p>
                <p className="text-3xl font-bold tracking-tight">
                  Actif
                </p>
              </div>
              
              {/* Prix */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">{t("subscriptionPage.price")}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold tracking-tight">
                    299
                  </span>
                  <span className="text-sm text-muted-foreground">
                    MAD / {t("subscriptionPage.month")}
                  </span>
                </div>
              </div>
            </div>

            {!subscription?.is_access_allowed && (
              <Alert variant="destructive">
                <AlertTitle>Accès suspendu</AlertTitle>
                <AlertDescription>{t("subscriptionPage.expiredMessage")}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Features Card */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle>{t("subscriptionPage.included")}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ul className="grid gap-3 sm:grid-cols-2">
              {features.map((featureKey) => {
                const Icon = featureIcons[featureKey] || Check;
                return (
                  <li key={featureKey} className="flex items-start gap-3">
                    <div className="mt-0.5 flex-shrink-0 rounded-full bg-primary/10 p-1">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <p className="text-sm text-foreground">
                      {t(`subscriptionPage.features.${featureKey}`, featureKey)}
                    </p>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>

        {/* Usage Section */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle>Utilisation de la plateforme</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[1,2,3,4,5,6].map((i) => (
                  <div key={i} className="space-y-1">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-6 w-16" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Upload className="h-4 w-4" />
                    <span>Nombre d'imports</span>
                  </div>
                  <p className="text-2xl font-bold tracking-tight">
                    {uploads.length > 0 ? uploads.length : "Non disponible"}
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>Historique disponible</span>
                  </div>
                  <p className="text-2xl font-bold tracking-tight">
                    {treasuryProfile?.historical_months != null ? `${Math.round(treasuryProfile.historical_months)} mois` : "Non disponible"}
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>Dernière mise à jour</span>
                  </div>
                  <p className="text-2xl font-bold tracking-tight">
                    {(() => {
                      const latestUpload = uploads[0];
                      if (latestUpload?.created_at) {
                        return formatDate(latestUpload.created_at, {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                        });
                      }
                      return "Non disponible";
                    })()}
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <TrendingUp className="h-4 w-4" />
                    <span>Prévisions activées</span>
                  </div>
                  <p className="text-2xl font-bold tracking-tight">
                    {typeof treasuryProfile?.forecasting_enabled === "boolean" ? (treasuryProfile.forecasting_enabled ? "Oui" : "Non") : "Non disponible"}
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Database className="h-4 w-4" />
                    <span>Observations historiques</span>
                  </div>
                  <p className="text-2xl font-bold tracking-tight">
                    {(() => {
                      // Check treasury profile first for historical_days or total_records
                      if (treasuryProfile?.historical_days != null) {
                        return `${treasuryProfile.historical_days} jours`;
                      }
                      if (treasuryProfile?.total_records != null) {
                        return `${treasuryProfile.total_records} enregistrements`;
                      }
                      // Check analytics data
                      if (analyticsData?.kpis?.historical_days != null) {
                        return `${analyticsData.kpis.historical_days} jours`;
                      }
                      if (analyticsData?.kpis?.total_records != null) {
                        return `${analyticsData.kpis.total_records} enregistrements`;
                      }
                      return "Non disponible";
                    })()}
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <ShieldCheck className="h-4 w-4" />
                    <span>Qualité des données</span>
                  </div>
                  <p className="text-2xl font-bold tracking-tight">
                    {(() => {
                      const maturity = treasuryProfile?.data_maturity || analyticsData?.kpis?.data_maturity;
                      if (maturity) {
                        const map = {
                          "low": "FAIBLE",
                          "medium": "MOYEN",
                          "good": "BON",
                          "optimal": "EXCELLENT",
                          "excellent": "EXCELLENT"
                        };
                        return map[maturity] || maturity.toUpperCase();
                      }
                      return "Non disponible";
                    })()}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          {canActivate && (
            <Button onClick={handleActivate} disabled={actionLoading}>
              {actionLoading ? t("subscription.activating") : t("subscriptionPage.activate")}
            </Button>
          )}
          {canCancel && status !== "expired" && (
            <Button variant="outline" onClick={handleCancel} disabled={actionLoading}>
              {t("subscriptionPage.cancel")}
            </Button>
          )}
          <Link to="/" className={cn(buttonVariants({ variant: "ghost" }))}>
            {t("subscriptionPage.backDashboard")}
          </Link>
        </div>
      </div>
    </div>
  );
}
