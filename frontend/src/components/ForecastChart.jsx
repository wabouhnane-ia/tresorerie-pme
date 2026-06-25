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
  ReferenceArea,
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
  ShieldCheck,
  AlertCircle,
  Landmark,
  CalendarRange,
  BarChart4,
} from "lucide-react";

function ForecastChart({ data, treasuryBalance }) {
  const { formatDate, t } = useTranslation();
  const { theme } = useTheme();
  const hasData = Array.isArray(data) && data.length > 0;

  // Colors adapted to theme
  const getReferenceLineColors = () => {
    if (theme === 'dark') {
      return {
        stroke: 'hsl(var(--muted-foreground) / 0.18)',
        labelFill: 'hsl(var(--muted-foreground) / 0.7)',
      };
    } else {
      return {
        stroke: 'hsl(var(--muted-foreground) / 0.15)',
        labelFill: 'hsl(var(--muted-foreground) / 0.8)',
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
  
  // Calculate trend color based on trend
  const trendColor =
    trend === "up"
      ? "hsl(var(--chart-2))"
      : trend === "down"
        ? "hsl(var(--chart-4))"
        : "hsl(var(--primary))";
        
  const primaryColor = "hsl(var(--primary))";
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

  // Premium Executive Insight Tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const dataPoint = payload[0].payload;
    const variationFromStart = dataPoint.projectedBalance - treasuryBalance;
    const variationPercentFromStart = treasuryBalance !== 0 ? (variationFromStart / treasuryBalance) * 100 : 0;
    const isPositive = variationFromStart >= 0;

    return (
      <div className="rounded-2xl border border-border/60 bg-card/95 p-5 shadow-2xl backdrop-blur-md">
        {/* Top Row with Date */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
              <Calendar className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">{t("common.date")}</p>
              <p className="text-sm font-semibold text-foreground">
                {formatDate(dataPoint.ds, { 
                  day: '2-digit', 
                  month: 'long',
                  year: 'numeric'
                })}
              </p>
            </div>
          </div>
          <Badge 
            variant={isPositive ? "default" : "destructive"}
            className="text-[11px] px-2 py-0.5 rounded-full"
          >
            {isPositive ? (
              <><TrendingUp className="h-3.5 w-3.5 mr-1" /> En hausse</>
            ) : (
              <><TrendingDown className="h-3.5 w-3.5 mr-1" /> En baisse</>
            )}
          </Badge>
        </div>
        
        <Separator className="my-3" />
        
        {/* Main Projected Balance */}
        <div className="mb-4">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
            {t("forecast.projectedBalance")}
          </p>
          <p className="text-2xl font-bold" style={{ color: trendColor }}>
            {formatMad(dataPoint.projectedBalance)}
          </p>
        </div>
        
        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Variation Percentage */}
          <div className="space-y-1">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              {t("forecast.variation")}
            </p>
            <div className="flex items-center gap-1.5">
              {isPositive ? (
                <ArrowUpRight className="h-4 w-4 text-emerald-500" />
              ) : (
                <ArrowDownRight className="h-4 w-4 text-red-500" />
              )}
              <span className={`text-base font-bold ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
                {isPositive ? '+' : ''}{variationPercentFromStart.toFixed(1)}%
              </span>
            </div>
          </div>
          
          {/* Variation Amount */}
          <div className="space-y-1">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Montant
            </p>
            <span className={`text-base font-bold ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
              {isPositive ? '+' : ''}{formatMad(variationFromStart)}
            </span>
          </div>
        </div>
        
        {/* Reference Level */}
        <div className="flex items-center justify-between bg-muted/30 p-3 rounded-xl mb-3">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
            {t("forecast.currentLevel")}
          </span>
          <span className="text-sm font-semibold text-foreground">
            {formatMad(treasuryBalance)}
          </span>
        </div>
        
        {/* Confidence Interval */}
        {(dataPoint.confidenceLow || dataPoint.confidenceHigh) && (
          <div className="bg-gradient-to-r from-primary/5 to-transparent p-3 rounded-xl border border-primary/10">
            <div className="flex items-center gap-2 mb-1.5">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <span className="text-[11px] font-medium text-primary uppercase tracking-wider">
                {t("forecast.confidenceInterval")}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground/70">
                {formatMadCompact(dataPoint.confidenceLow)}
              </span>
              <AlertCircle className="h-3 w-3 text-muted-foreground/50" />
              <span className="text-muted-foreground/70">
                {formatMadCompact(dataPoint.confidenceHigh)}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Custom current level badge
  const CurrentLevelBadge = () => {
    return (
      <div className="absolute right-5 top-20 bg-card/95 border border-border/60 rounded-lg px-3 py-1.5 shadow-sm backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full" style={{ background: referenceLineColors.stroke }} />
          <span className="text-xs font-medium text-muted-foreground">Current Treasury</span>
        </div>
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
          <div className="flex flex-col items-center justify-center rounded-2xl bg-muted/30 py-20 px-8 ring-1 ring-border/50">
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-muted/30">
              <Activity className="h-10 w-10 text-muted-foreground/50" />
            </div>
            <p className="text-base font-semibold text-foreground mb-2 text-center">
              {t("forecast.insufficientData")}
            </p>
            <p className="text-sm text-muted-foreground/70 text-center max-w-md">
              {t("forecast.importMore")}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/50 bg-card shadow-xl">
      {/* Premium Header */}
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
          
          {/* Status Indicator */}
          <div className="flex items-center gap-2 rounded-full bg-muted/30 px-4 py-2 ring-1 ring-border/50">
            {trend === "up" && (
              <>
                <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-semibold text-emerald-500">{t("forecast.healthyCash")}</span>
              </>
            )}
            {trend === "down" && (
              <>
                <div className="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs font-semibold text-red-500">{t("forecast.watchRequired")}</span>
              </>
            )}
            {trend === "stable" && (
              <>
                <div className="h-2.5 w-2.5 rounded-full bg-blue-500" />
                <span className="text-xs font-semibold text-blue-500">{t("forecast.stable")}</span>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-8">
        {/* Premium KPI Cards */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {/* KPI 1: Current Balance */}
          <div className="group relative overflow-hidden rounded-xl bg-muted/30 p-4 ring-1 ring-border/50 transition-all hover:ring-primary/50 hover:shadow-lg hover:shadow-primary/5">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-600/5 ring-1 ring-blue-500/20 shadow-sm">
                  <Landmark className="h-4 w-4 text-blue-600" />
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

          {/* KPI 2: Projected Balance */}
          <div className="group relative overflow-hidden rounded-xl bg-muted/30 p-4 ring-1 ring-border/50 transition-all hover:ring-primary/50 hover:shadow-lg hover:shadow-primary/5">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/10 to-purple-600/5 ring-1 ring-purple-500/20 shadow-sm">
                  {trend === "up" ? <TrendingUp className="h-4 w-4 text-purple-600" /> : trend === "down" ? <TrendingDown className="h-4 w-4 text-purple-600" /> : <Activity className="h-4 w-4 text-purple-600" />}
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
                <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                  kpis.variation >= 0 
                    ? 'bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 ring-1 ring-emerald-500/20 shadow-sm' 
                    : 'bg-gradient-to-br from-red-500/10 to-red-600/5 ring-1 ring-red-500/20 shadow-sm'
                }`}>
                  <BarChart4 className={`h-4 w-4 ${kpis.variation >= 0 ? 'text-emerald-600' : 'text-red-600'}`} />
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
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 ring-1 ring-cyan-500/20 shadow-sm">
                  <CalendarRange className="h-4 w-4 text-cyan-600" />
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

        {/* Premium Chart */}
        <div className="rounded-2xl bg-muted/30 p-6 ring-1 ring-border/50 relative">
          {/* Current Treasury Badge */}
          <CurrentLevelBadge />
          
          {/* Elegant Legend with Badges */}
          <div className="flex items-center justify-end gap-4 mb-5 pb-4 border-b border-border/30">
            <Badge variant="outline" className="flex items-center gap-2 px-3 py-1 bg-transparent">
              <div className="h-1.5 w-4 rounded-full" style={{ background: `linear-gradient(to right, ${trendColor}, ${trendColor})` }} />
              <span className="text-xs font-medium text-muted-foreground">{t("forecast.projection")}</span>
            </Badge>
            <Badge variant="outline" className="flex items-center gap-2 px-3 py-1 bg-transparent">
              <div 
                className="h-1.5 w-4 rounded-full"
                style={{ 
                  background: referenceLineColors.stroke,
                  backgroundImage: `repeating-linear-gradient(
                    to right,
                    ${referenceLineColors.stroke} 0,
                    ${referenceLineColors.stroke} 2px,
                    transparent 2px,
                    transparent 5px
                  )`
                }}
              />
              <span className="text-xs font-medium text-muted-foreground">{t("forecast.currentLevel")}</span>
            </Badge>
          </div>
          
          <ResponsiveContainer width="100%" height={420}>
            <AreaChart 
              data={chartData} 
              margin={{ top: 30, right: 30, left: 10, bottom: 20 }}
            >
              <defs>
                {/* Confidence band gradient - only surrounds the line */}
                <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={trendColor} stopOpacity={theme === 'dark' ? 0.1 : 0.07} />
                  <stop offset="50%" stopColor={trendColor} stopOpacity={theme === 'dark' ? 0.05 : 0.03} />
                  <stop offset="100%" stopColor={trendColor} stopOpacity={theme === 'dark' ? 0.015 : 0.01} />
                </linearGradient>
                
                {/* Glow filter */}
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3.2" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              
              {/* Ultra Subtle Grid */}
              <CartesianGrid 
                strokeDasharray="0" 
                stroke="hsl(var(--border) / 0.06)" 
                strokeWidth={1}
                vertical={false}
              />
              
              <XAxis
                dataKey="ds"
                tickFormatter={formatXAxis}
                stroke="hsl(var(--muted-foreground) / 0.18)"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: 'hsl(var(--border) / 0.12)', strokeWidth: 1 }}
                tick={{ fill: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)' }}
                dy={10}
                tickMargin={8}
              />
              
              <YAxis
                tickFormatter={(value) => formatMadCompact(value)}
                stroke="hsl(var(--muted-foreground) / 0.18)"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: 'hsl(var(--border) / 0.12)', strokeWidth: 1 }}
                tick={{ fill: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)' }}
                width={90}
                dx={-5}
                tickMargin={8}
              />
              
              <Tooltip 
                content={<CustomTooltip />} 
                cursor={{ 
                  stroke: trendColor, 
                  strokeWidth: 1,
                  strokeDasharray: '8 8',
                  opacity: 0.25
                }} 
              />
              
              {/* Confidence Band - only surrounds the line */}
              <Area
                type="monotone"
                dataKey="confidenceHigh"
                stroke="transparent"
                fill="transparent"
              />
              <Area
                type="monotone"
                dataKey="confidenceLow"
                stroke="transparent"
                fill="url(#colorConfidence)"
              />
              
              {/* Current Treasury Reference Line */}
              <ReferenceLine
                y={treasuryBalance}
                stroke={referenceLineColors.stroke}
                strokeDasharray="10 5"
                strokeWidth={0.7}
              />
              
              {/* Main Forecast Line */}
              <Line
                type="monotone"
                dataKey="projectedBalance"
                stroke="var(--foreground)"
                strokeWidth={3.5}
                dot={false}
                activeDot={{ 
                  r: 8, 
                  fill: "var(--foreground)", 
                  strokeWidth: 5, 
                  stroke: "var(--card)",
                  filter: "url(#glow)"
                }}
                animationDuration={1300}
                animationEasing="ease-in-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        
        {/* Footer info */}
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
