import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { useTranslation } from "../i18n/LanguageProvider";
import { formatDate } from "../utils/localeFormat";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { ScrollArea } from "./ui/scroll-area";
import { CheckCircle2, Circle, Clock, TrendingUp } from "lucide-react";

const MONTH_NAMES = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

function formatMonthKey(key) {
  if (!key || key.length < 7) return key;
  const [year, month] = key.split("-");
  const monthIdx = parseInt(month, 10) - 1;
  return `${MONTH_NAMES[monthIdx] || month} ${year}`;
}

function hasObservedImpact(entry) {
  const impact = safeGet(entry, "impact", null);
  return Boolean(
    impact &&
      (impact.runway_delta != null ||
        impact.resilience_delta != null ||
        impact.health_delta != null)
  );
}

function StageItem({ active, icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 rounded-full border p-1 ${active ? "border-primary text-primary" : "border-border text-muted-foreground"}`}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">{value}</p>
      </div>
    </div>
  );
}

function TimelineEntry({ entry }) {
  const { t } = useTranslation();
  const status = safeGet(entry, "status", "pending");
  const impact = safeGet(entry, "impact", null);
  const completedAt = safeGet(entry, "completed_at", null);
  const impactAvailable = hasObservedImpact(entry);

  return (
    <Card className="border-border bg-muted/20">
      <CardHeader className="space-y-2 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-sm leading-snug">{entry.decision_title}</CardTitle>
            <CardDescription>{formatDate(entry.decision_date)}</CardDescription>
          </div>
          <Badge variant={status === "completed" ? "default" : "secondary"} className="shrink-0 text-xs">
            {t(`decisions.status.${status}`)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="grid gap-3 md:grid-cols-4">
          <StageItem
            active
            icon={Circle}
            label="Création"
            value={formatDate(entry.decision_date)}
          />
          <StageItem
            active={status === "in_progress" || status === "completed"}
            icon={Clock}
            label="Validation"
            value={status === "pending" ? "En attente" : "Validée"}
          />
          <StageItem
            active={status === "completed"}
            icon={CheckCircle2}
            label="Réalisation"
            value={completedAt ? formatDate(completedAt) : status === "completed" ? "Réalisée" : "En attente"}
          />
          <StageItem
            active={impactAvailable}
            icon={TrendingUp}
            label="Impact observé"
            value={impactAvailable ? "Mesuré" : "Impact en cours d'évaluation"}
          />
        </div>

        {impactAvailable && (
          <>
            <Separator />
            <div className="grid gap-2 text-xs md:grid-cols-3">
              {impact.runway_delta != null && (
                <p>
                  Runway: {impact.runway_delta > 0 ? "+" : ""}{impact.runway_delta} {t("common.days")}
                </p>
              )}
              {impact.resilience_delta != null && (
                <p>
                  Résilience: {impact.resilience_delta > 0 ? "+" : ""}{impact.resilience_delta} points
                </p>
              )}
              {impact.health_delta != null && (
                <p>
                  Santé financière: {impact.health_delta > 0 ? "+" : ""}{impact.health_delta} points
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function DecisionTimeline({ history }) {
  const { t } = useTranslation();
  const byMonth = safeGet(history, "by_month", {});
  const monthKeys = Object.keys(byMonth).sort().reverse();

  if (!monthKeys.length) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center">
          <p className="text-sm text-muted-foreground">{t("decisions.noTimeline")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="text-xl">Timeline décisionnelle</CardTitle>
        <CardDescription>
          Création, validation, réalisation et impact observé regroupés par mois.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[520px] pr-3">
          <div className="space-y-8">
            {monthKeys.map((monthKey) => (
              <div key={monthKey} className="space-y-4">
                <div className="flex items-center gap-3">
                  <Separator className="flex-1" />
                  <Badge variant="secondary" className="text-xs uppercase tracking-wide">
                    {formatMonthKey(monthKey)}
                  </Badge>
                  <Separator className="flex-1" />
                </div>
                <div className="space-y-3">
                  {ensureArray(byMonth[monthKey]).map((entry) => (
                    <TimelineEntry key={entry.decision_id} entry={entry} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
