import { safeGet } from "../utils/safeDataAccess";
import { getLocaleTag } from "../i18n/i18n";
import { formatDateTime } from "../utils/localeFormat";
import { useTranslation } from "../i18n/LanguageProvider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import {
  BarChart3,
  CalendarClock,
  CheckCircle2,
  Database,
  History,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";

const MINIMUM_HISTORY_MONTHS = 24;
const RECOMMENDED_HISTORY_MONTHS = 36;
const OPTIMAL_HISTORY_MONTHS = 48;

function formatNumber(value, options = {}) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString(getLocaleTag(), options);
}

function formatMonths(value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return `${formatNumber(value, { maximumFractionDigits: 1 })} mois`;
}

function getMaturityLabel(value) {
  if (!value) return "-";

  const normalized = String(value).toLowerCase();
  const labels = {
    insufficient: "Insufficient",
    poor: "Poor",
    ready: "Ready",
    medium: "Medium",
    advanced: "Advanced",
    good: "Good",
    optimal: "Optimal",
    excellent: "Excellent",
  };

  return labels[normalized] || String(value);
}

function isOnboardingComplete(onboardingInfo) {
  const status = String(safeGet(onboardingInfo, "status", "")).toUpperCase();
  return (
    safeGet(onboardingInfo, "onboarding_completed", false) === true ||
    safeGet(onboardingInfo, "forecasting_enabled", false) === true ||
    ["READY", "MINIMUM_READY", "OPTIMAL"].includes(status)
  );
}

function StatItem({ icon: Icon, label, value, children }) {
  return (
    <div className="rounded-md border border-border bg-background p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </div>
      <div className="mt-2 text-xl font-semibold tracking-tight text-foreground">
        {children || value}
      </div>
    </div>
  );
}

function TreasuryMemoryActiveCard({ onboardingInfo, treasuryProfile }) {
  const historicalMonths = safeGet(
    treasuryProfile,
    "historical_months",
    safeGet(onboardingInfo, "historical_months", null)
  );
  const totalObservations = safeGet(
    onboardingInfo,
    "records_loaded",
    safeGet(treasuryProfile, "total_observations", null)
  );
  const dataMaturity = safeGet(
    onboardingInfo,
    "data_maturity",
    safeGet(treasuryProfile, "history_level", null)
  );
  const forecastEnabled = safeGet(onboardingInfo, "forecasting_enabled", null);
  const lastUpdate = safeGet(
    treasuryProfile,
    "updated_at",
    safeGet(
      treasuryProfile,
      "last_uploaded_date",
      safeGet(treasuryProfile, "latest_data_date", safeGet(onboardingInfo, "date_max", null))
    )
  );

  const getIntelligenceLevelLabel = (maturity) => {
    switch (maturity) {
      case "optimal": return "Expert";
      case "advanced": return "Avancé";
      case "ready": return "Standard";
      default: return "Initial";
    }
  };

  const getForecastIntelligenceStatus = (maturity) => {
    switch (maturity) {
      case "optimal":
      case "advanced":
      case "ready":
        return "Active";
      default:
        return "En préparation";
    }
  };

  return (
    <Card className="border-border">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-lg font-semibold">
              <Database className="h-5 w-5" />
              Treasury Memory Active
            </CardTitle>
            <CardDescription>
              ✓ Intelligence Trésorerie activée
            </CardDescription>
          </div>
          <Badge variant={forecastEnabled ? "default" : "outline"} className="w-fit">
            {getForecastIntelligenceStatus(dataMaturity)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatItem icon={History} label="Historique disponible" value={formatMonths(historicalMonths)} />
          <StatItem
            icon={BarChart3}
            label="Total observations"
            value={formatNumber(totalObservations)}
          />
          <StatItem icon={ShieldCheck} label="Niveau d'intelligence">
            <Badge variant="secondary" className="text-sm">
              {getIntelligenceLevelLabel(dataMaturity)}
            </Badge>
          </StatItem>
          <StatItem icon={TrendingUp} label="Prévisions">
            <Badge variant={forecastEnabled ? "default" : "outline"} className="text-sm">
              Opérationnelles
            </Badge>
          </StatItem>
          <StatItem icon={CalendarClock} label="Dernière mise à jour" value={formatDateTime(lastUpdate)} />
        </div>
      </CardContent>
    </Card>
  );
}

function OnboardingCard({ onboardingInfo }) {
  const { t } = useTranslation();
  const historicalMonths = safeGet(onboardingInfo, "historical_months", 0);
  const status = safeGet(onboardingInfo, "status", "NO_DATA");
  const progress = Math.min(100, (historicalMonths / MINIMUM_HISTORY_MONTHS) * 100);
  const monthsRemaining = Math.max(0, MINIMUM_HISTORY_MONTHS - historicalMonths);

  const getStatusTitle = () => {
    if (status === "NO_DATA") return t("onboarding.titleNoData");
    if (status === "INSUFFICIENT_HISTORY") return t("onboarding.titleInsufficient");
    if (status === "MINIMUM_READY") return t("onboarding.titleReady");
    return t("onboarding.titleOptimal");
  };

  const getStatusMessage = () => {
    if (status === "NO_DATA") return t("onboarding.msgNoData");
    if (status === "INSUFFICIENT_HISTORY") return t("onboarding.msgInsufficient");
    if (status === "MINIMUM_READY") return t("onboarding.msgReady");
    return t("onboarding.msgOptimal", { months: historicalMonths });
  };

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg font-semibold">
          <History className="h-5 w-5" />
          {getStatusTitle()}
        </CardTitle>
        <CardDescription>{getStatusMessage()}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <StatItem icon={Database} label={t("onboarding.monthsImported")} value={formatMonths(historicalMonths)} />
          <StatItem
            icon={CheckCircle2}
            label={t("onboarding.minimumRequired")}
            value={formatMonths(MINIMUM_HISTORY_MONTHS)}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">
              {t("onboarding.progress", { pct: Math.round(progress) })}
            </span>
            <span className="text-muted-foreground">
              {t("onboarding.monthsRemaining", { count: Math.ceil(monthsRemaining) })}
            </span>
          </div>
          <Progress value={progress} />
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {[
            {
              label: t("onboarding.milestoneMinimum"),
              value: MINIMUM_HISTORY_MONTHS,
              reached: historicalMonths >= MINIMUM_HISTORY_MONTHS,
            },
            {
              label: t("onboarding.milestoneRecommended"),
              value: RECOMMENDED_HISTORY_MONTHS,
              reached: historicalMonths >= RECOMMENDED_HISTORY_MONTHS,
            },
            {
              label: t("onboarding.milestoneOptimal"),
              value: `${OPTIMAL_HISTORY_MONTHS}+`,
              reached: historicalMonths >= OPTIMAL_HISTORY_MONTHS,
            },
          ].map((milestone) => (
            <div key={milestone.label} className="rounded-md border border-border p-3">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs font-medium text-muted-foreground">{milestone.label}</p>
                  <p className="text-lg font-semibold">{milestone.value} {t("common.months")}</p>
                </div>
                {milestone.reached && <CheckCircle2 className="h-5 w-5 text-primary" />}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function OnboardingStatusCard({ onboardingInfo, treasuryProfile }) {
  if (!onboardingInfo) {
    return null;
  }

  const historicalMonths = safeGet(
    treasuryProfile,
    "historical_months",
    safeGet(onboardingInfo, "historical_months", 0)
  );
  const onboardingComplete = isOnboardingComplete(onboardingInfo);
  const shouldShowOnboarding =
    !onboardingComplete || Number(historicalMonths) < MINIMUM_HISTORY_MONTHS;

  if (shouldShowOnboarding) {
    return <OnboardingCard onboardingInfo={onboardingInfo} />;
  }

  return (
    <TreasuryMemoryActiveCard
      onboardingInfo={onboardingInfo}
      treasuryProfile={treasuryProfile}
    />
  );
}

export default OnboardingStatusCard;
