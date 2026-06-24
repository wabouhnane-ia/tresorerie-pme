import { useEffect, useState } from "react";
import API from "../services/api";
import { analyticsService } from "../services/analyticsService";
import { useTranslation } from "../i18n/LanguageProvider";
import { notificationService } from "../services/notificationService";
import { useNotificationShell } from "../contexts/NotificationShellContext";
import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { formatMad, formatMadCompact } from "../utils/localeFormat";
import ForecastChart from "../components/ForecastChart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { Skeleton } from "../components/ui/skeleton";
import { Button } from "../components/ui/button";
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Calendar } from "lucide-react";

export default function ForecastPage() {
  const { t, language } = useTranslation();
  const [kpis, setKpis] = useState({});
  const [forecast, setForecast] = useState([]);
  const [businessIntelligence, setBusinessIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const { openNotificationCenter } = useNotificationShell();
  const [isForecastRunning, setIsForecastRunning] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const res = await API.get('/forecast/status');
        if (!mounted) return;
        setIsForecastRunning(!!res.data.running);
      } catch (err) {
        console.warn('Could not fetch forecast status', err);
      }
    };

    fetchStatus();

    // Poll while a run is active to re-enable UI when finished
    const interval = setInterval(fetchStatus, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    fetchData();
  }, [language]);

  const fetchData = async () => {
    try {
      const latestRes = await API.get("/analytics/latest-analysis");
      if (latestRes.data.has_real_data) {
        const kpisData = safeGet(latestRes.data, "kpis", {});
        setKpis(kpisData);
        setForecast(ensureArray(safeGet(latestRes.data, "forecast", [])));
        setBusinessIntelligence(safeGet(latestRes.data, "business_intelligence", null));
      }
    } catch (err) {
      console.error("Could not fetch forecast data:", err);
    } finally {
      setLoading(false);
    }
  };

  const treasuryBalance = safeGet(kpis, "treasury_balance", 0);
  const runwayDays = safeGet(kpis, "cash_runway_days", 0);
  const topRisks = ensureArray(safeGet(businessIntelligence, "top_risks", []));
  const topDecisions = ensureArray(safeGet(businessIntelligence, "top_decisions", []));

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Card className="border-border">
          <CardContent className="pt-6">
            <Skeleton className="h-40 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Executive Forecast Summary */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">{t("nav.forecasts")}</h1>
        <p className="text-muted-foreground">{t("forecast.pageSubtitle")}</p>
        <div className="pt-2">
          <Button
            onClick={async () => {
              if (retraining || isForecastRunning) return;
              setRetraining(true);
              setIsForecastRunning(true);
              try {
                await analyticsService.trainForecastModels();
                await fetchData();
                await notificationService.createNotification({
                  notification_type: "success",
                  severity: "low",
                  title: t("forecast.retrainSuccess"),
                  message: t("forecast.retrainSuccessDetail"),
                });
                openNotificationCenter();
              } catch (err) {
                console.error("Retrain failed:", err);
                if (err?.response?.status === 409) {
                  // Server indicates a run is already in progress
                  await notificationService.createNotification({
                    notification_type: "warning",
                    severity: "high",
                    title: t("forecast.alreadyRunning"),
                    message: t("forecast.alreadyRunningDetail"),
                  });
                } else {
                  await notificationService.createNotification({
                    notification_type: "warning",
                    severity: "high",
                    title: t("forecast.retrainError"),
                    message: err?.message || String(err) || t("forecast.retrainErrorDetail"),
                  });
                }
                openNotificationCenter();
              } finally {
                setRetraining(false);
              }
            }}
            disabled={retraining || isForecastRunning}
          >
            {retraining || isForecastRunning ? t("forecast.retraining") : t("forecast.retrain")}
          </Button>
        </div>
      </div>

      <Separator />

      {/* Forecast Chart */}
      <ForecastChart data={forecast} treasuryBalance={treasuryBalance} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Projection 30 Days */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              {t("forecast.projection30")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {forecast.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">{t("forecast.projectedBalance")}</span>
                  <span className="font-semibold text-foreground">
                    {formatMad(
                      // yhat is already the absolute treasury balance at each date, not a delta
                      forecast.length > 0 
                        ? Number(forecast[forecast.length - 1].yhat) || treasuryBalance 
                        : treasuryBalance
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">{t("forecast.runway")}</span>
                  <Badge variant={runwayDays > 90 ? "default" : runwayDays > 30 ? "secondary" : "destructive"}>
                    {runwayDays} {t("common.days")}
                  </Badge>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">{t("forecast.insufficientProjection")}</p>
            )}
          </CardContent>
        </Card>

        {/* Projection 90 Days (Placeholder) */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              {t("forecast.projection90")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{t("forecast.projection90MoreData")}</p>
          </CardContent>
        </Card>

        {/* Risques Forecast */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              {t("forecast.forecastRisks")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {topRisks.length > 0 ? (
              topRisks.slice(0, 3).map((risk, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 mt-0.5 text-destructive" />
                  <div>
                    <p className="font-medium text-foreground">{safeGet(risk, "title", "")}</p>
                    <p className="text-sm text-muted-foreground">{safeGet(risk, "description", "")}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground">{t("forecast.noRisks")}</p>
            )}
          </CardContent>
        </Card>

        {/* Recommandations Forecast */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              {t("forecast.forecastRecommendations")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {topDecisions.length > 0 ? (
              topDecisions.slice(0, 3).map((decision, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-primary" />
                  <div>
                    <p className="font-medium text-foreground">{safeGet(decision, "action", "")}</p>
                    <p className="text-sm text-muted-foreground">{safeGet(decision, "business_justification", "")}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground">{t("forecast.noRecommendations")}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
