import { useTranslation } from "../i18n/LanguageProvider";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Database, History, ShieldCheck, Calendar, Clock } from "lucide-react";

export default function TreasuryMemoryCard({
  profile
}) {
  const { formatDate, t } = useTranslation();
  
  const getIntelligenceLevelVariant = (maturity) => {
    switch (maturity) {
      case "optimal": return "default";
      case "advanced": return "default";
      case "ready": return "secondary";
      default: return "outline";
    }
  };

  const getIntelligenceLevelLabel = (maturity) => {
    switch (maturity) {
      case "optimal": return t("treasuryMemory.expert");
      case "advanced": return t("treasuryMemory.advanced");
      case "ready": return t("treasuryMemory.standard");
      default: return t("treasuryMemory.initial");
    }
  };

  const getIntelligenceLevelDescription = (maturity) => {
    switch (maturity) {
      case "optimal": return t("treasuryMemory.optimalDescription");
      case "advanced": return t("treasuryMemory.advancedDescription");
      case "ready": return t("treasuryMemory.readyDescription");
      default: return t("treasuryMemory.initialDescription");
    }
  };

  const getForecastIntelligenceStatus = (maturity) => {
    switch (maturity) {
      case "optimal":
      case "advanced":
      case "ready":
        return t("treasuryMemory.active");
      default:
        return t("treasuryMemory.preparing");
    }
  }

  if (!profile) {
    return null;
  }

  return (
    <Card className="w-full border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="w-5 h-5" />
          {t("treasuryMemory.title")}
        </CardTitle>
        <CardDescription>{t("treasuryMemory.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <History className="w-4 h-4" />
              <span>{t("treasuryMemory.historyAvailable")}</span>
            </div>
            <p className="text-xl font-bold">
              {Math.round(profile.historical_months)} {t("common.months")}
            </p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>{t("treasuryMemory.observations")}</span>
            </div>
            <p className="text-xl font-bold">{profile.historical_days} {t("common.days")}</p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ShieldCheck className="w-4 h-4" />
              <span>{t("treasuryMemory.intelligenceLevel")}</span>
            </div>
            <Badge variant={getIntelligenceLevelVariant(profile.history_level)} className="text-base px-3">
              {getIntelligenceLevelLabel(profile.history_level)}
            </Badge>
            <p className="text-xs text-muted-foreground">{getIntelligenceLevelDescription(profile.history_level)}</p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="w-4 h-4" />
              <span>{t("treasuryMemory.forecastIntelligence")}</span>
            </div>
            <Badge variant={getForecastIntelligenceStatus(profile.history_level) === "Active" ? "default" : "outline"} className="text-base px-3">
              {getForecastIntelligenceStatus(profile.history_level)}
            </Badge>
          </div>
        </div>
        {profile.latest_data_date && (
          <>
            <Separator />
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{t("treasuryMemory.lastUpdate")}</span>
              <span className="font-medium">
                {formatDate(profile.latest_data_date, {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                })}
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
