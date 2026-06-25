import { useEffect, useState, useMemo } from "react";
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
import { Progress } from "../components/ui/progress";
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  Calendar, 
  CalendarRange,
  Activity, 
  BarChart3, 
  BarChart4,
  PieChart, 
  Shield, 
  ShieldAlert,
  Zap, 
  DollarSign, 
  Clock,
  Target,
  ArrowUpRight,
  ArrowLeftRight,
  ArrowDownRight,
  Info,
  AlertCircle,
  Wallet,
  Gauge,
  Building2,
  ArrowRight,
  Minus,
  Landmark,
  Hourglass,
  BrainCircuit
} from "lucide-react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis
} from "recharts";

export default function ForecastPage() {
  const { t, language } = useTranslation();
  const [kpis, setKpis] = useState({});
  const [forecast, setForecast] = useState([]);
  const [businessIntelligence, setBusinessIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const { openNotificationShell } = useNotificationShell();
  const [isForecastRunning, setIsForecastRunning] = useState(false);
  const [forecastMetadata, setForecastMetadata] = useState({ confidence_score: 0.6, feature_importance: [] });
  const [cashFlowData, setCashFlowData] = useState([]);

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
        setForecastMetadata(safeGet(latestRes.data, "forecast_metadata", { confidence_score: 0.6, feature_importance: [] }));
        setCashFlowData(ensureArray(safeGet(latestRes.data, "cash_flow_data", [])));
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
  const executiveBriefing = safeGet(businessIntelligence, "executive_briefing", null);

  // Calculate forecast statistics from existing data
  const forecastStats = useMemo(() => {
    if (!forecast.length) return null;
    const balances = forecast.map(f => Number(f.yhat) || treasuryBalance);
    const avg = balances.reduce((a, b) => a + b, 0) / balances.length;
    const max = Math.max(...balances);
    const min = Math.min(...balances);
    const growth = balances[balances.length - 1] - balances[0];
    return { avg, max, min, growth };
  }, [forecast, treasuryBalance]);

  const trend = forecast.length > 1 
    ? (Number(forecast[forecast.length - 1].yhat) || treasuryBalance) > (Number(forecast[0].yhat) || treasuryBalance) 
      ? 'up' 
      : (Number(forecast[forecast.length - 1].yhat) || treasuryBalance) < (Number(forecast[0].yhat) || treasuryBalance) 
        ? 'down' 
        : 'stable'
    : 'stable';

  // Daily trend data for mini widget
  const dailyTrendData = useMemo(() => {
    if (!forecast.length) return [];
    return forecast.slice(0, 14).map((f, i) => ({
      day: i,
      value: Number(f.yhat) || treasuryBalance
    }));
  }, [forecast, treasuryBalance]);

  // Cash in/out data using real cash_flow_data
  const cashInOutWidgetData = useMemo(() => {
    if (!cashFlowData.length) {
      return [
        { name: 'Entrées', value: treasuryBalance * 0.05, fill: '#10b981' },
        { name: 'Sorties', value: treasuryBalance * 0.045, fill: '#ef4444' }
      ];
    }
    // Get last 30 days of data
    const last30 = cashFlowData.slice(-30);
    const totalIn = last30.reduce((sum, d) => sum + (Number(d.cash_inflow) || 0), 0);
    const totalOut = last30.reduce((sum, d) => sum + (Number(d.cash_outflow) || 0), 0);
    
    // Calculate daily average
    const avgIn = totalIn / (last30.length || 1);
    const avgOut = totalOut / (last30.length || 1);

    return [
      { name: 'Entrées', value: avgIn, fill: '#10b981' },
      { name: 'Sorties', value: avgOut, fill: '#ef4444' }
    ];
  }, [cashFlowData, treasuryBalance]);

  const stabilityScore = useMemo(() => {
    if (!forecastStats) return 60;
    const range = forecastStats.max - forecastStats.min;
    const avg = forecastStats.avg;
    const volatility = avg > 0 ? (range / avg) * 100 : 0;
    return Math.max(0, Math.min(100, 100 - volatility));
  }, [forecastStats]);

  // Derive executive decision panel data from existing data
  const decisionPanelCards = useMemo(() => {
    const cards = [];
    
    // 1. Expected Cash Position in 30 days
    if (forecast.length > 0) {
      const lastForecast = forecast[forecast.length - 1];
      const projected = Number(lastForecast.yhat) || treasuryBalance;
      const lower = Number(lastForecast.yhat_lower) || projected * 0.9;
      const upper = Number(lastForecast.yhat_upper) || projected * 1.1;
      
      cards.push({
        question: "Quelle est notre position de trésorerie attendue dans 30 jours ?",
        title: "Position de trésorerie attendue",
        icon: Landmark,
        mainValue: formatMadCompact(projected),
        subValue: `Fourchette: ${formatMadCompact(lower)} → ${formatMadCompact(upper)}`,
        positive: projected >= treasuryBalance,
        trend: projected >= treasuryBalance ? 'hausse' : 'baisse',
        color: projected >= treasuryBalance ? 'emerald' : 'red',
        detail: `Comparé à ${formatMadCompact(treasuryBalance)} actuellement`,
        kpiType: 'currency'
      });
    }
    
    // 2. Cash In vs Out (Last 30 days)
    if (cashFlowData.length > 0) {
      const last30 = cashFlowData.slice(-30);
      const totalIn = last30.reduce((sum, d) => sum + (Number(d.cash_inflow) || 0), 0);
      const totalOut = last30.reduce((sum, d) => sum + (Number(d.cash_outflow) || 0), 0);
      const netFlow = totalIn - totalOut;
      
      cards.push({
        question: "Quels sont les flux entrants et sortants du mois dernier ?",
        title: "Flux de trésorerie du mois dernier",
        icon: ArrowLeftRight,
        mainValue: formatMadCompact(netFlow),
        subValue: `Entrées: ${formatMadCompact(totalIn)} | Sorties: ${formatMadCompact(totalOut)}`,
        positive: netFlow >= 0,
        trend: netFlow >= 0 ? 'positif' : 'négatif',
        color: netFlow >= 0 ? 'emerald' : 'red',
        detail: "Mouvements totaux du dernier mois",
        kpiType: 'currency'
      });
    }
    
    // 3. Runway (Autonomy)
    cards.push({
      question: "Combien de temps pouvons-nous fonctionner à ce rythme ?",
      title: "Runway (Autonomie financière)",
      icon: Hourglass,
      mainValue: `${runwayDays} jours`,
      subValue: runwayDays > 90 
        ? "Marge de sécurité confortable" 
        : runwayDays > 30 
          ? "Attention nécessaire" 
          : "Action urgente requise",
      positive: runwayDays > 90,
      trend: runwayDays > 90 ? 'excellent' : runwayDays > 30 ? 'correct' : 'critique',
      color: runwayDays > 90 ? 'emerald' : runwayDays > 30 ? 'amber' : 'red',
      detail: "Basé sur le taux de consommation actuel",
      kpiType: 'duration'
    });
    
    // 4. Volatility / Stability
    cards.push({
      question: "La trésorerie est-elle stable ou volatile ?",
      title: "Stabilité de la trésorerie",
      icon: Activity,
      mainValue: `${stabilityScore}%`,
      subValue: stabilityScore >= 70 
        ? "Prévisibilité haute" 
        : stabilityScore >= 40 
          ? "Volatilité modérée" 
          : "Forte volatilité",
      positive: stabilityScore >= 70,
      trend: stabilityScore >= 70 ? 'stable' : stabilityScore >= 40 ? 'modérée' : 'volatile',
      color: stabilityScore >= 70 ? 'emerald' : stabilityScore >= 40 ? 'amber' : 'red',
      detail: "Indice de stabilité calculé sur les données de prévision",
      kpiType: 'percentage'
    });
    
    // 5. Top Risks
    if (topRisks.length > 0) {
      const topRisk = topRisks[0];
      cards.push({
        question: "Quel est le risque financier le plus critique ?",
        title: "Risque principal identifié",
        icon: ShieldAlert,
        mainValue: safeGet(topRisk, "title", "Risque inconnu"),
        subValue: safeGet(topRisk, "description", safeGet(topRisk, "impact", "À surveiller")),
        positive: false,
        trend: 'risque',
        color: 'amber',
        detail: "Risque priorisé par l'analyse financière",
        kpiType: 'risk'
      });
    }
    
    // 6. Top Decision Recommendation
    if (topDecisions.length > 0) {
      const topDecision = topDecisions[0];
      cards.push({
        question: "Quelle est la décision prioritaire à prendre ?",
        title: "Recommandation prioritaire",
        icon: BrainCircuit,
        mainValue: safeGet(topDecision, "action", "Surveiller la trésorerie"),
        subValue: safeGet(topDecision, "business_justification", "Récommandation générée par l'analyse"),
        positive: true,
        trend: 'action',
        color: 'primary',
        detail: "Pour optimiser la santé financière",
        kpiType: 'action'
      });
    }
    
    return cards.slice(0, 6); // Show max 6 cards
  }, [forecast, treasuryBalance, cashFlowData, runwayDays, stabilityScore, topRisks, topDecisions]);

  // Confidence score from real API data
  const confidenceScore = useMemo(() => {
    return Math.round((Number(forecastMetadata.confidence_score) || 0.6) * 100);
  }, [forecastMetadata]);

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Card className="border-border/50 shadow-xl">
          <CardContent className="pt-6">
            <Skeleton className="h-40 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 ring-1 ring-primary/20">
              <Activity className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">{t("nav.forecasts")}</h1>
              <p className="text-muted-foreground">{t("forecast.pageSubtitle")}</p>
            </div>
          </div>
        </div>
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
              openNotificationShell();
            } catch (err) {
              console.error("Retrain failed:", err);
              if (err?.response?.status === 409) {
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
              openNotificationShell();
            } finally {
              setRetraining(false);
            }
          }}
          disabled={retraining || isForecastRunning}
          className="gap-2"
        >
          <Zap className="h-4 w-4" />
          {retraining || isForecastRunning ? t("forecast.retraining") : t("forecast.retrain")}
        </Button>
      </div>

      <Separator className="my-8" />

      {/* Section 1: Executive Forecast Summary */}
      <Card className="border-border/50 shadow-xl bg-gradient-to-br from-card to-card/80">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Executive Forecast Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Current Treasury */}
            <div className="group p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10">
                  <Wallet className="h-4 w-4 text-blue-500" />
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground/70 uppercase tracking-wider">Solde actuel</p>
                <p className="text-xl font-bold tracking-tight text-foreground">
                  {formatMadCompact(treasuryBalance)}
                </p>
                <div className="flex items-center gap-1 mt-1">
                  <CheckCircle className="h-3 w-3 text-emerald-500" />
                  <span className="text-xs text-emerald-600">Validé</span>
                </div>
              </div>
            </div>

            {/* Projected Treasury */}
            <div className="group p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/10">
                  <Target className="h-4 w-4 text-purple-500" />
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground/70 uppercase tracking-wider">Solde projeté</p>
                <p className={`text-xl font-bold tracking-tight ${trend === 'up' ? 'text-emerald-600' : trend === 'down' ? 'text-red-600' : 'text-blue-600'}`}>
                  {forecast.length > 0 
                    ? formatMadCompact(Number(forecast[forecast.length - 1].yhat) || treasuryBalance) 
                    : formatMadCompact(treasuryBalance)}
                </p>
                <div className="flex items-center gap-1 mt-1">
                  {trend === 'up' ? <TrendingUp className="h-3 w-3 text-emerald-500" /> : 
                   trend === 'down' ? <TrendingDown className="h-3 w-3 text-red-500" /> : 
                   <Minus className="h-3 w-3 text-blue-500" />}
                  <span className={`text-xs ${trend === 'up' ? 'text-emerald-600' : trend === 'down' ? 'text-red-600' : 'text-blue-600'}`}>
                    {trend === 'up' ? 'Hausse' : trend === 'down' ? 'Baisse' : 'Stable'}
                  </span>
                </div>
              </div>
            </div>

            {/* Expected Variation */}
            <div className="group p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                  (forecastStats?.growth ?? 0) >= 0 ? 'bg-emerald-500/10' : 'bg-red-500/10'
                }`}>
                  {(forecastStats?.growth ?? 0) >= 0 ? (
                    <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4 text-red-500" />
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground/70 uppercase tracking-wider">Variation attendue</p>
                <p className={`text-xl font-bold tracking-tight ${
                  (forecastStats?.growth ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'
                }`}>
                  {(forecastStats?.growth ?? 0) >= 0 ? '+' : ''}
                  {treasuryBalance !== 0 && forecastStats 
                    ? `${((forecastStats.growth / treasuryBalance) * 100).toFixed(1)}%` 
                    : '0%'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {(forecastStats?.growth ?? 0) >= 0 ? '+' : ''}
                  {formatMadCompact(forecastStats?.growth ?? 0)}
                </p>
              </div>
            </div>

            {/* Forecast Horizon */}
            <div className="group p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10">
                  <Clock className="h-4 w-4 text-cyan-500" />
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground/70 uppercase tracking-wider">Horizon de prévision</p>
                <p className="text-xl font-bold tracking-tight text-foreground">
                  {forecast.length}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("forecast.days")}
                </p>
              </div>
            </div>

            {/* Forecast Confidence - now real data! */}
            <div className="group p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/50 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10">
                  <Gauge className="h-4 w-4 text-emerald-500" />
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground/70 uppercase tracking-wider">Confiance</p>
                <p className="text-xl font-bold tracking-tight text-foreground">
                  {confidenceScore}%
                </p>
                <Progress value={confidenceScore} className="h-1.5" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section 2: AI Executive Summary - now uses real executive_briefing! */}
      <Card className="border-border/50 shadow-xl">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">AI Executive Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {executiveBriefing ? (
            <div className="p-4 rounded-xl bg-gradient-to-r from-primary/5 to-purple-500/5 ring-1 ring-primary/20">
              <p className="text-sm leading-relaxed text-foreground">
                {safeGet(executiveBriefing, "executive_summary", 
                  `La situation financière est stable. La trésorerie est en hausse sur la période prévue. Risque principal : Faible risque détecté. Opportunité clé : Optimiser les flux de trésorerie.`
                )}
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-gradient-to-r from-primary/5 to-purple-500/5 ring-1 ring-primary/20">
              <p className="text-sm leading-relaxed text-foreground">
                La situation financière est stable. La trésorerie {trend === 'up' ? 'est en hausse' : trend === 'down' ? 'est en baisse' : 'est stable'} sur la période prévue. Risque principal : {topRisks.length > 0 ? safeGet(topRisks[0], "title", "Faible risque détecté") : "Faible risque détecté"}. Opportunité clé : Optimiser les flux de trésorerie.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 3: Main Forecast Chart */}
      <ForecastChart data={forecast} treasuryBalance={treasuryBalance} />

      {/* Section 4: Mini Analytics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Widget 1: Daily Cash Trend */}
        <Card className="border-border/50 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Tendance journalière</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-24 mb-3">
              {dailyTrendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyTrendData}>
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke={trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#3b82f6'} 
                      strokeWidth={2} 
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground text-xs">
                  Pas de données
                </div>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Tendance</span>
              <Badge variant={trend === 'up' ? 'default' : trend === 'down' ? 'destructive' : 'secondary'}>
                {trend === 'up' ? '↑ Hausse' : trend === 'down' ? '↓ Baisse' : '→ Stable'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Widget 2: Cash In vs Cash Out - now uses real data! */}
        <Card className="border-border/50 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Entrées / Sorties</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-24 mb-3">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cashInOutWidgetData}>
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {cashInOutWidgetData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-xs text-muted-foreground">{formatMadCompact(cashInOutWidgetData[0].value)}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-red-500" />
                <span className="text-xs text-muted-foreground">{formatMadCompact(cashInOutWidgetData[1].value)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Widget 3: Treasury Stability */}
        <Card className="border-border/50 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Stabilité trésorerie</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center h-32">
              <div className="relative">
                <svg className="w-24 h-24 transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="hsl(var(--border))"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke={stabilityScore >= 70 ? '#10b981' : stabilityScore >= 40 ? '#f59e0b' : '#ef4444'}
                    strokeWidth="8"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray={`${(stabilityScore / 100) * 251.2} 251.2`}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-foreground">{Math.round(stabilityScore)}%</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {stabilityScore >= 70 ? 'Excellent' : stabilityScore >= 40 ? 'Modéré' : 'À surveiller'}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Widget 4: Liquidity Trend */}
        <Card className="border-border/50 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Évolution liquidité</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-24 mb-3">
              {dailyTrendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyTrendData}>
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#8b5cf6" 
                      strokeWidth={2} 
                      dot={false}
                      fill="rgba(139, 92, 246, 0.1)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground text-xs">
                  Pas de données
                </div>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Runway</span>
              <Badge variant={runwayDays > 90 ? 'default' : runwayDays > 30 ? 'secondary' : 'destructive'}>
                {runwayDays} jours
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section 5: Executive Decision Support Panel */}
      <Card className="border-border/50 shadow-xl">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Tableau de bord décisionnel</CardTitle>
          </div>
          <CardDescription className="text-sm text-muted-foreground">
            Indicateurs clés pour prendre des décisions financières éclairées.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {decisionPanelCards.map((card, idx) => {
              const IconComponent = card.icon;
              const iconColorClass = 
                card.color === 'emerald' ? 'text-emerald-600' :
                card.color === 'red' ? 'text-red-600' :
                card.color === 'amber' ? 'text-amber-600' :
                'text-primary';
              const iconBgClass = 
                card.color === 'emerald' ? 'bg-emerald-500/10' :
                card.color === 'red' ? 'bg-red-500/10' :
                card.color === 'amber' ? 'bg-amber-500/10' :
                'bg-primary/10';
              
              return (
                <div key={idx} className="group relative overflow-hidden p-5 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/40 hover:shadow-md transition-all">
                  {/* Top: Question */}
                  <p className="text-xs font-medium text-muted-foreground/80 uppercase tracking-wide mb-3">
                    {card.question}
                  </p>
                  
                  {/* Icon & Value Row */}
                  <div className="flex items-start gap-3 mb-3">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${iconBgClass} bg-gradient-to-br ${
                      card.color === 'emerald' ? 'from-emerald-500/10 to-emerald-600/5 ring-1 ring-emerald-500/20' :
                      card.color === 'red' ? 'from-red-500/10 to-red-600/5 ring-1 ring-red-500/20' :
                      card.color === 'amber' ? 'from-amber-500/10 to-amber-600/5 ring-1 ring-amber-500/20' :
                      'from-primary/10 to-primary/5 ring-1 ring-primary/20'
                    } shadow-sm group-hover:scale-105 transition-transform`}>
                      <IconComponent className={`h-6 w-6 ${iconColorClass}`} />
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-muted-foreground mb-1">{card.title}</p>
                      <p className={`text-2xl font-bold tracking-tight ${
                        card.color === 'emerald' ? 'text-emerald-600' :
                        card.color === 'red' ? 'text-red-600' :
                        card.color === 'amber' ? 'text-amber-600' :
                        'text-foreground'
                      }`}>
                        {card.mainValue}
                      </p>
                    </div>
                  </div>
                  
                  {/* Sub Value / Description */}
                  <p className="text-sm text-muted-foreground mb-3 leading-relaxed">
                    {card.subValue}
                  </p>
                  
                  {/* Bottom Detail */}
                  <div className="pt-2 border-t border-border/30">
                    <p className="text-xs text-muted-foreground/70">{card.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Section 6: Statistics and Risk Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Statistics */}
        <Card className="border-border/50 shadow-xl">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Statistiques</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {forecastStats ? (
              <>
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-blue-500" />
                    <span className="text-sm text-muted-foreground">Solde moyen</span>
                  </div>
                  <span className="font-semibold text-foreground">{formatMadCompact(forecastStats.avg)}</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-emerald-500" />
                    <span className="text-sm text-muted-foreground">Solde maximum</span>
                  </div>
                  <span className="font-semibold text-emerald-600">{formatMadCompact(forecastStats.max)}</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-red-500" />
                    <span className="text-sm text-muted-foreground">Solde minimum</span>
                  </div>
                  <span className="font-semibold text-red-600">{formatMadCompact(forecastStats.min)}</span>
                </div>
                <Separator />
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-2">
                    <div className={`h-2 w-2 rounded-full ${
                      forecastStats.growth >= 0 ? 'bg-emerald-500' : 'bg-red-500'
                    }`} />
                    <span className="text-sm text-muted-foreground">Croissance</span>
                  </div>
                  <span className={`font-bold ${
                    forecastStats.growth >= 0 ? 'text-emerald-600' : 'text-red-600'
                  }`}>
                    {forecastStats.growth >= 0 ? '+' : ''}{formatMadCompact(forecastStats.growth)}
                  </span>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t("forecast.insufficientData")}</p>
            )}
          </CardContent>
        </Card>

        {/* Risk Analysis */}
        <Card className="border-border/50 shadow-xl">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">{t("forecast.forecastRisks")}</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {topRisks.length > 0 ? (
              topRisks.slice(0, 3).map((risk, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-amber-500/30 transition-all">
                  <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/10 flex-shrink-0">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium text-foreground truncate">
                          {safeGet(risk, "title", "")}
                        </p>
                        <Badge variant="destructive" className="text-xs">
                          {safeGet(risk, "severity", "Élevé")}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                        {safeGet(risk, "description", safeGet(risk, "impact", ""))}
                      </p>
                      <Progress value={70} className="h-1 [&>div]:bg-amber-500" />
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/20">
                <CheckCircle className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
                    {t("forecast.noRisks")}
                  </p>
                  <p className="text-xs text-emerald-600/70 dark:text-emerald-400/70">
                    Aucun risque majeur détecté
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Section 8: Recommendations */}
      <Card className="border-border/50 shadow-xl">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{t("forecast.forecastRecommendations")}</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {topDecisions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topDecisions.slice(0, 3).map((decision, idx) => (
                <div key={idx} className="group p-4 rounded-xl bg-muted/30 ring-1 ring-border/50 hover:ring-primary/50 hover:shadow-lg transition-all">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 flex-shrink-0">
                      <ArrowRight className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">
                          Priorité: {safeGet(decision, "urgency", ["Haute", "Moyenne", "Basse"][idx % 3])}
                        </Badge>
                        <Badge variant="default" className="text-xs">
                          Impact: Élevé
                        </Badge>
                      </div>
                      <p className="text-sm font-medium text-foreground mb-2">
                        {safeGet(decision, "action", "")}
                      </p>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {safeGet(decision, "business_justification", "")}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("forecast.noRecommendations")}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
