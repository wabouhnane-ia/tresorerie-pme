import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
  AreaChart,
  Legend,
} from "recharts";
import { useTranslation } from "../i18n/LanguageProvider";
import { useTheme } from "../hooks/useTheme";
import { formatMad, formatMadCompact } from "../utils/localeFormat";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Calendar, 
  Wallet, 
  Target,
  Clock, 
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  CircleDashed
} from "lucide-react";

function ForecastChart({ data, treasuryBalance }) {
  const { formatDate, t } = useTranslation();
  const { theme } = useTheme();
  const hasData = Array.isArray(data) && data.length > 0;

  // Couleurs adaptatives au thème pour la ligne de référence
  const getReferenceLineColors = () => {
    if (theme === 'dark') {
      return {
        stroke: 'rgba(96, 165, 250, 0.4)', // blue-400 avec transparence
        labelFill: 'rgba(96, 165, 250, 0.8)',
      };
    } else {
      return {
        stroke: 'rgba(71, 85, 105, 0.5)', // slate-600 avec transparence
        labelFill: 'rgba(51, 65, 85, 0.9)', // slate-700
      };
    }
  };

  const referenceLineColors = getReferenceLineColors();

  const chartData = (() => {
    if (!hasData || typeof treasuryBalance !== "number") return [];

    let projectedBalance = treasuryBalance;
    return [...data]
      .sort((a, b) => new Date(a.ds).valueOf() - new Date(b.ds).valueOf())
      .map((point, index) => {
        // Each `yhat` is already the forecasted level (treasury balance) for that date.
        // Do NOT sum yhat values. Use the yhat (or fallback to current projectedBalance).
        const pointYhat = Number(point.yhat ?? projectedBalance);
        const confidenceLow = point.yhat_lower != null ? Number(point.yhat_lower) : pointYhat * 0.95;
        const confidenceHigh = point.yhat_upper != null ? Number(point.yhat_upper) : pointYhat * 1.05;
        projectedBalance = pointYhat;
        return {
          ds: point.ds,
          projectedBalance,
          confidenceLow,
          confidenceHigh,
          isToday: index === 0,
        };
      });
  })();

  const getTrend = () => {
    if (chartData.length < 2) return "stable";
    const firstValue = chartData[0].projectedBalance;
    const lastValue = chartData[chartData.length - 1].projectedBalance;
    if (lastValue > firstValue) return "up";
    if (lastValue < firstValue) return "down";
    return "stable";
  };

  const getKPIs = () => {
    if (chartData.length === 0) {
      return {
        currentBalance: treasuryBalance,
        projectedBalance: treasuryBalance,
        variation: 0,
        variationPercent: 0,
        horizon: 0,
      };
    }

    const projectedBalance = chartData[chartData.length - 1].projectedBalance;
    const variation = projectedBalance - treasuryBalance;
    const variationPercent = treasuryBalance !== 0 ? (variation / treasuryBalance) * 100 : 0;
    const horizon = chartData.length;

    return {
      currentBalance: treasuryBalance,
      projectedBalance,
      variation,
      variationPercent,
      horizon,
    };
  };

  const trend = getTrend();
  const kpis = getKPIs();
  const trendColor = trend === "up" ? "hsl(var(--chart-2))" : trend === "down" ? "hsl(var(--chart-1))" : "hsl(var(--primary))";
  const trendLabel =
    trend === "up"
      ? t("forecast.trendUp")
      : trend === "down"
        ? t("forecast.trendDown")
        : t("forecast.trendStable");

  const formatXAxis = (dateStr) => {
    const date = new Date(dateStr);
    if (Number.isNaN(date.valueOf())) return dateStr;
    return `${String(date.getDate()).padStart(2, "0")}/${String(date.getMonth() + 1).padStart(2, "0")}`;
  };

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const dataPoint = payload[0].payload;
    const variationFromStart = dataPoint.projectedBalance - treasuryBalance;
    const variationPercentFromStart = treasuryBalance !== 0 ? (variationFromStart / treasuryBalance) * 100 : 0;
    const isPositive = variationFromStart >= 0;

    return (
      <div className="rounded-xl border border-border/50 bg-card p-4 shadow-2xl backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Calendar className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">{t("common.date")}</p>
            <p className="text-sm font-semibold text-foreground">
              {formatDate(dataPoint.ds, { 
                day: '2-digit', 
                month: 'long' 
              })}
            </p>
          </div>
        </div>
        
        <div className="h-px bg-border/50 my-3" />
        
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs font-medium text-muted-foreground">{t("forecast.projectedBalance")}</span>
            <span className="text-lg font-bold" style={{ color: trendColor }}>
              {formatMadCompact(dataPoint.projectedBalance)}
            </span>
          </div>
          
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs font-medium text-muted-foreground">{t("forecast.currentLevel")}</span>
            <span className="text-sm font-semibold text-foreground">
              {formatMadCompact(treasuryBalance)}
            </span>
          </div>
          
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs font-medium text-muted-foreground">{t("forecast.variation")}</span>
            <div className="flex items-center gap-1.5">
              {isPositive ? (
                <ArrowUpRight className="h-3.5 w-3.5 text-emerald-500" />
              ) : (
                <ArrowDownRight className="h-3.5 w-3.5 text-red-500" />
              )}
              <span className={`text-sm font-semibold ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
                {isPositive ? '+' : ''}{variationPercentFromStart.toFixed(1)}%
              </span>
            </div>
          </div>
          
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs font-medium text-muted-foreground">{t("forecast.amount")}</span>
            <span className={`text-xs font-medium ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
              {isPositive ? '+' : ''}{formatMadCompact(variationFromStart)}
            </span>
          </div>
        </div>
        
        {(dataPoint.confidenceLow || dataPoint.confidenceHigh) && (
          <>
            <div className="h-px bg-border/50 my-3" />
            <div className="text-[10px] text-muted-foreground/70 flex items-center gap-1">
              <Activity className="h-3 w-3" />
              <span>{t("forecast.confidenceInterval")}</span>
            </div>
          </>
        )}
      </div>
    );
  };

  if (!hasData || typeof treasuryBalance !== "number") {
    return (
      <Card className="border-border/50 bg-card shadow-xl">
        <CardHeader className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
              <Activity className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-xl font-bold tracking-tight">
                {t("forecast.title")}
              </CardTitle>
              <CardDescription className="text-sm text-muted-foreground/80">
                {t("forecast.subtitle")}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center rounded-xl bg-muted/30 py-16 px-8 ring-1 ring-border/50">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/30">
              <Activity className="h-8 w-8 text-muted-foreground/50" />
            </div>
            <p className="text-sm font-medium text-foreground mb-2 text-center">
              {t("forecast.insufficientData")}
            </p>
            <p className="text-xs text-muted-foreground/70 text-center max-w-sm">
              {t("forecast.importMore")}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/50 bg-card shadow-xl">
      {/* SECTION 1 — Premium Header */}
      <CardHeader className="space-y-4 pb-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                <Activity className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl font-bold tracking-tight">
                  {t("forecast.title")}
                </CardTitle>
                <CardDescription className="text-sm text-muted-foreground/80">
                  {t("forecast.subtitle")}
                </CardDescription>
              </div>
            </div>
          </div>
          
          {/* Status Indicator - Discret */}
          <div className="flex items-center gap-2 rounded-full bg-muted/30 px-3 py-1.5 ring-1 ring-border/50">
            {trend === "up" && (
              <>
                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-medium text-emerald-500">{t("forecast.healthyCash")}</span>
              </>
            )}
            {trend === "down" && (
              <>
                <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs font-medium text-red-500">{t("forecast.watchRequired")}</span>
              </>
            )}
            {trend === "stable" && (
              <>
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-xs font-medium text-blue-500">{t("forecast.stable")}</span>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-8">
        {/* SECTION 2 — Premium KPI Cards */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {/* KPI 1: Solde actuel */}
          <div className="group relative overflow-hidden rounded-xl bg-muted/30 p-4 ring-1 ring-border/50 transition-all hover:ring-primary/50 hover:shadow-lg hover:shadow-primary/5">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10">
                  <Wallet className="h-4 w-4 text-blue-500" />
                </div>
                <div className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                  {t("forecast.currentShort")}
                </div>
              </div>
              <div>
                <p className="text-2xl font-bold tracking-tight text-foreground">
                  {formatMadCompact(kpis.currentBalance)}
                </p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {t("forecast.currentBalance")}
                </p>
              </div>
            </div>
          </div>

          {/* KPI 2: Solde projeté */}
          <div className="group relative overflow-hidden rounded-xl bg-muted/30 p-4 ring-1 ring-border/50 transition-all hover:ring-primary/50 hover:shadow-lg hover:shadow-primary/5">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/10">
                  <Target className="h-4 w-4 text-purple-500" />
                </div>
                <div className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                  {t("forecast.projection")}
                </div>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <p className="text-2xl font-bold tracking-tight" style={{ color: trendColor }}>
                    {formatMadCompact(kpis.projectedBalance)}
                  </p>
                  {trend === "up" && <TrendingUp className="h-4 w-4 text-emerald-500" />}
                  {trend === "down" && <TrendingDown className="h-4 w-4 text-red-500" />}
                  {trend === "stable" && <Minus className="h-4 w-4 text-blue-500" />}
                </div>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {t("forecast.projectedBalance")}
                </p>
              </div>
            </div>
          </div>

          {/* KPI 3: Variation */}
          <div className="group relative overflow-hidden rounded-xl bg-muted/30 p-4 ring-1 ring-border/50 transition-all hover:ring-primary/50 hover:shadow-lg hover:shadow-primary/5">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative space-y-3">
              <div className="flex items-center justify-between">
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                  kpis.variation >= 0 ? 'bg-emerald-500/10' : 'bg-red-500/10'
                }`}>
                  {kpis.variation >= 0 ? (
                    <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4 text-red-500" />
                  )}
                </div>
                <div className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                  Delta
                </div>
              </div>
              <div>
                <p className={`text-2xl font-bold tracking-tight ${
                  kpis.variation >= 0 ? 'text-emerald-500' : 'text-red-500'
                }`}>
                  {kpis.variation >= 0 ? "+" : ""}
                  {kpis.variationPercent.toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {kpis.variation >= 0 ? "+" : ""}
                  {formatMadCompact(kpis.variation)}
                </p>
              </div>
            </div>
          </div>

          {/* KPI 4: Horizon */}
          <div className="group relative overflow-hidden rounded-xl bg-muted/30 p-4 ring-1 ring-border/50 transition-all hover:ring-primary/50 hover:shadow-lg hover:shadow-primary/5">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10">
                  <Clock className="h-4 w-4 text-cyan-500" />
                </div>
                <div className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                  Période
                </div>
              </div>
              <div>
                <div className="flex items-baseline gap-1.5">
                  <p className="text-2xl font-bold tracking-tight text-foreground">
                    {kpis.horizon}
                  </p>
                  <p className="text-sm font-medium text-muted-foreground">
                    {t("forecast.days")}
                  </p>
                </div>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {t("forecast.forecastHorizon")}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 3 — Premium Chart */}
        <div className="rounded-xl bg-muted/30 p-6 ring-1 ring-border/50">
          {/* Légende élégante */}
          <div className="flex items-center justify-end gap-6 mb-4 pb-3 border-b border-border/30">
            <div className="flex items-center gap-2">
              <div className="h-0.5 w-6 rounded-full" style={{ background: `linear-gradient(to right, ${trendColor}, ${trendColor})` }} />
              <span className="text-xs font-medium text-muted-foreground">{t("forecast.projection")}</span>
            </div>
            <div className="flex items-center gap-2">
              <div 
                className="h-0.5 w-6 rounded-full"
                style={{ 
                  background: referenceLineColors.stroke,
                  backgroundImage: `repeating-linear-gradient(
                    to right,
                    ${referenceLineColors.stroke} 0,
                    ${referenceLineColors.stroke} 4px,
                    transparent 4px,
                    transparent 8px
                  )`
                }}
              />
              <span className="text-xs font-medium text-muted-foreground">{t("forecast.currentLevel")}</span>
            </div>
          </div>
          
          <ResponsiveContainer width="100%" height={420}>
            <AreaChart 
              data={chartData} 
              margin={{ top: 20, right: 30, left: 10, bottom: 20 }}
            >
              <defs>
                <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={trendColor} stopOpacity={0.25} />
                  <stop offset="50%" stopColor={trendColor} stopOpacity={0.1} />
                  <stop offset="95%" stopColor={trendColor} stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="colorLine" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={trendColor} stopOpacity={0.8} />
                  <stop offset="100%" stopColor={trendColor} stopOpacity={1} />
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              
              <CartesianGrid 
                strokeDasharray="0" 
                stroke="hsl(var(--border) / 0.2)" 
                strokeWidth={1}
                vertical={false}
              />
              
              <XAxis
                dataKey="ds"
                tickFormatter={formatXAxis}
                stroke="hsl(var(--muted-foreground) / 0.3)"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: 'hsl(var(--border) / 0.3)', strokeWidth: 1 }}
                tick={{ fill: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)' }}
                dy={10}
              />
              
              <YAxis
                tickFormatter={(value) => formatMadCompact(value)}
                stroke="hsl(var(--muted-foreground) / 0.3)"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: 'hsl(var(--border) / 0.3)', strokeWidth: 1 }}
                tick={{ fill: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)' }}
                width={90}
                dx={-5}
              />
              
              <Tooltip 
                content={<CustomTooltip />} 
                cursor={{ 
                  stroke: trendColor, 
                  strokeWidth: 1,
                  strokeDasharray: '5 5',
                  opacity: 0.5
                }} 
              />
              
              <ReferenceLine
                y={treasuryBalance}
                stroke={referenceLineColors.stroke}
                strokeDasharray="8 4"
                strokeWidth={1.5}
                label={{
                  position: "insideTopRight",
                  value: t("forecast.currentLevel"),
                  fill: referenceLineColors.labelFill,
                  fontSize: 10,
                  fontWeight: 600,
                  offset: 10,
                  opacity: 0.9
                }}
              />
              
              <Area
                type="monotone"
                dataKey="confidenceLow"
                stroke="transparent"
                fill="transparent"
              />
              
              <Area
                type="monotone"
                dataKey="confidenceHigh"
                stroke="transparent"
                fill="url(#colorConfidence)"
              />
              
              <Line
                type="monotone"
                dataKey="projectedBalance"
                stroke="url(#colorLine)"
                strokeWidth={3}
                dot={false}
                activeDot={{ 
                  r: 6, 
                  fill: trendColor, 
                  strokeWidth: 3, 
                  stroke: "hsl(var(--card))",
                  filter: "url(#glow)"
                }}
                name={t("forecast.projectedBalance")}
                animationDuration={1000}
                animationEasing="ease-in-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        
        {/* Footer info - subtil */}
        <div className="flex items-center justify-between text-[11px] text-muted-foreground/50">
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-primary/50" />
            <span>{t("forecast.liveData")}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Activity className="h-3 w-3" />
            <span>{t("forecast.basedOnDays", { days: kpis.horizon })}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default ForecastChart;
