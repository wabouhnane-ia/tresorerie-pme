import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { useTranslation } from "../i18n/LanguageProvider";
import {
  translateHealthLabel,
  translateProbability,
  translateResilienceLabel,
  translateRiskTitle,
  translateSeverity,
  translateUrgency,
} from "../utils/translateApiValue";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { Separator } from "./ui/separator";

const getScoreBadgeVariant = (category) => {
  if (category === "excellent" || category === "healthy") return "default";
  if (category === "vigilance" || category === "moderate") return "secondary";
  if (category === "fragile") return "secondary";
  return "destructive";
};

const getSeverityVariant = (severity) => {
  const s = String(severity || "").toLowerCase();
  if (s === "critical" || s === "critique") return "destructive";
  if (s === "high" || s === "élevé" || s === "élevée") return "destructive";
  if (s === "medium" || s === "moyen" || s === "moyenne") return "secondary";
  return "default";
};

function ScoreCard({ title, score, label, category, children }) {
  return (
    <Card className="border-border">
      <CardHeader className="space-y-1">
        <CardDescription className="text-xs">{title}</CardDescription>
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-bold tracking-tight">{score}</span>
          <span className="text-sm text-muted-foreground">/100</span>
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Badge variant={getScoreBadgeVariant(category)} className="text-xs">
            {label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground leading-relaxed">{children}</div>
      </CardContent>
    </Card>
  );
}

function BriefingBlock({ title, children }) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        {title}
      </h4>
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  );
}

function BusinessIntelligenceSection({ intelligence }) {
  const { t } = useTranslation();

  if (!intelligence) return null;

  const health = intelligence.financial_health_score ?? {};
  const resilience = intelligence.treasury_resilience_score ?? {};
  const runway = intelligence.cash_runway ?? {};
  const alerts = ensureArray(intelligence.smart_alerts);
  const risks = ensureArray(intelligence.top_risks);
  const decisions = ensureArray(intelligence.top_decisions);
  const briefing = intelligence.executive_briefing ?? {};

  const mainRisk = safeGet(briefing, "main_risk", {});
  const mainOpportunity = safeGet(briefing, "main_opportunity", {});
  const recommendedDecision = safeGet(briefing, "recommended_decision", {});
  const immediateActions = ensureArray(safeGet(briefing, "immediate_actions", []));

  return (
    <div className="space-y-6">
      {/* SECTION 1 — Financial Health KPIs */}
      <div className="grid gap-4 md:grid-cols-3">
        <ScoreCard
          title={t("bi.financialHealth")}
          score={safeGet(health, "score", 0)}
          label={translateHealthLabel(safeGet(health, "label"), t)}
          category={safeGet(health, "category", "vigilance")}
        >
          {safeGet(health, "explanation", "")}
        </ScoreCard>

        <ScoreCard
          title={t("bi.resilienceScore")}
          score={safeGet(resilience, "score", 0)}
          label={translateResilienceLabel(safeGet(resilience, "label"), t)}
          category={safeGet(resilience, "category", "vigilance")}
        >
          {safeGet(resilience, "interpretation", "")}
          {ensureArray(safeGet(resilience, "drivers", [])).length > 0 && (
            <ul className="mt-2 space-y-1 text-xs">
              {ensureArray(safeGet(resilience, "drivers", []))
                .slice(0, 3)
                .map((driver, idx) => (
                  <li key={idx}>• {driver}</li>
                ))}
            </ul>
          )}
        </ScoreCard>

        <Card className="border-border">
          <CardHeader className="space-y-1">
            <CardDescription className="text-xs">{t("bi.runwayHorizon")}</CardDescription>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tracking-tight">{safeGet(runway, "days", 0)}</span>
              <span className="text-sm text-muted-foreground">{t("common.days")}</span>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <Badge variant={getScoreBadgeVariant(safeGet(runway, "level", "moderate"))} className="text-xs">
                {safeGet(runway, "months", 0)} {t("common.months")}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {safeGet(runway, "interpretation", "")}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* SECTION 2 — Executive Briefing */}
      {briefing && safeGet(briefing, "executive_summary") && (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">
          {t("bi.executiveBriefing")}
        </CardTitle>
        <CardDescription>
          {t("bi.executiveBriefingSubtitle")}
        </CardDescription>
      </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-sm leading-relaxed">{safeGet(briefing, "executive_summary")}</p>

            <Separator />

            <div className="grid gap-6 md:grid-cols-2">
              <BriefingBlock title={t("bi.financialSituation")}>
                {safeGet(briefing, "financial_situation")}
              </BriefingBlock>

              <BriefingBlock title={t("bi.cashPosition")}>
                {safeGet(briefing, "cash_position_analysis")}
              </BriefingBlock>

              <BriefingBlock title={t("bi.mainRisk")}>
                <p className="font-semibold">{translateRiskTitle(safeGet(mainRisk, "title"), t)}</p>
                <p className="mt-1 text-muted-foreground">{safeGet(mainRisk, "description")}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("bi.severity")}: {translateSeverity(safeGet(mainRisk, "severity"), t)} •{" "}
                  {t("bi.estimatedImpact")}: {safeGet(mainRisk, "estimated_financial_impact")}
                </p>
              </BriefingBlock>

              <BriefingBlock title={t("bi.mainOpportunity")}>
                <p className="font-semibold">{safeGet(mainOpportunity, "title")}</p>
                <p className="mt-1 text-muted-foreground">{safeGet(mainOpportunity, "description")}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("bi.benefit")}: {safeGet(mainOpportunity, "potential_benefit")}
                </p>
              </BriefingBlock>

              <BriefingBlock title={t("bi.outlook30")}>
                {safeGet(briefing, "outlook_30_days")}
              </BriefingBlock>

              <BriefingBlock title={t("bi.recommendedDecision")}>
                <p className="font-semibold">{safeGet(recommendedDecision, "action")}</p>
                <p className="mt-1 text-muted-foreground">{safeGet(recommendedDecision, "rationale")}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("bi.expectedOutcome")}: {safeGet(recommendedDecision, "expected_outcome")} •{" "}
                  {t("bi.urgency")}: {translateUrgency(safeGet(recommendedDecision, "urgency"), t)}
                </p>
              </BriefingBlock>
            </div>

            {/* SECTION 3 — Immediate Actions */}
            {immediateActions.length > 0 && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    {t("bi.immediateActions")}
                  </h4>
                  <div className="space-y-2">
                    {immediateActions.map((item, idx) => (
                      <div key={idx} className="flex gap-3 rounded-lg border border-border p-3">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                          {idx + 1}
                        </span>
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium">{safeGet(item, "action")}</p>
                          <p className="text-xs text-muted-foreground">{safeGet(item, "why")}</p>
                          <p className="text-xs text-muted-foreground">
                            {t("bi.deadline")}: {safeGet(item, "deadline")}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* SECTION 4 — Smart Alerts */}
      {alerts.length > 0 && (
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">{t("bi.attentionTitle")}</CardTitle>
            <CardDescription>{t("bi.attentionSubtitle")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.map((alert, idx) => (
              <Alert
                key={`${safeGet(alert, "title", "alert")}-${idx}`}
                variant={getSeverityVariant(safeGet(alert, "severity"))}
                className="border-border"
              >
                <AlertTitle className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span className="font-semibold">{safeGet(alert, "title")}</span>
                  <div className="flex flex-wrap gap-2">
                    {safeGet(alert, "requires_attention_today") && (
                      <Badge variant="destructive" className="text-xs">
                        {t("common.today")}
                      </Badge>
                    )}
                    <Badge variant={getSeverityVariant(safeGet(alert, "severity"))} className="text-xs">
                      {translateSeverity(safeGet(alert, "severity"), t)}
                    </Badge>
                  </div>
                </AlertTitle>
                <AlertDescription className="mt-2 space-y-1 text-sm">
                  <p>{safeGet(alert, "description")}</p>
                  <p className="text-xs">
                    <span className="font-medium">{t("common.impact")}:</span>{" "}
                    {safeGet(alert, "business_impact")}
                  </p>
                  <p className="text-xs">
                    <span className="font-medium">{t("common.action")}:</span>{" "}
                    {safeGet(alert, "recommended_action")}
                  </p>
                </AlertDescription>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* SECTION 5 & 6 — Top Risks & Top Decisions */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* SECTION 5 — Top Risks */}
        {risks.length > 0 && (
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">{t("bi.topRisks")}</CardTitle>
              <CardDescription>
                {t("bi.topRisksSubtitle")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {risks.map((risk, idx) => (
                <Card
                  key={`${safeGet(risk, "title", "risk")}-${idx}`}
                  className="border-border bg-muted/30"
                >
                  <CardHeader className="space-y-2 pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-sm font-semibold">
                        {idx + 1}. {translateRiskTitle(safeGet(risk, "title"), t)}
                      </CardTitle>
                      <Badge variant={getSeverityVariant(safeGet(risk, "severity"))} className="text-xs">
                        {translateSeverity(safeGet(risk, "severity"), t)}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                      <span>
                        {t("bi.probability")}: {translateProbability(safeGet(risk, "probability"), t)}
                      </span>
                      <span>•</span>
                      <span>
                        {t("bi.urgency")}: {translateUrgency(safeGet(risk, "urgency"), t)}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0 text-xs">
                    <p>
                      <span className="font-medium">{t("bi.financialImpact")}:</span>{" "}
                      {safeGet(risk, "estimated_financial_impact")}
                    </p>
                    <p>
                      <span className="font-medium">{t("common.action")}:</span>{" "}
                      {safeGet(risk, "recommended_action")}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </CardContent>
          </Card>
        )}

        {/* SECTION 6 — Top Decisions */}
        {decisions.length > 0 && (
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">{t("bi.topDecisions")}</CardTitle>
              <CardDescription>
                {t("bi.topDecisionsSubtitle")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {decisions.map((decision, idx) => (
                <Card
                  key={`${safeGet(decision, "action", "top-decision")}-${idx}`}
                  className="border-border bg-primary/5"
                >
                  <CardHeader className="space-y-2 pb-3">
                    <CardTitle className="text-sm font-semibold">
                      {idx + 1}. {safeGet(decision, "action")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0 text-xs">
                    <p>
                      <span className="font-medium">{t("bi.justification")}:</span>{" "}
                      {safeGet(decision, "business_justification")}
                    </p>
                    <p>
                      <span className="font-medium">{t("bi.expectedBenefit")}:</span>{" "}
                      {safeGet(decision, "expected_benefit")}
                    </p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      <Badge variant="secondary" className="text-xs">
                        {t("bi.urgency")}: {translateUrgency(safeGet(decision, "urgency"), t)}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {t("bi.horizon")}: {safeGet(decision, "time_horizon")}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default BusinessIntelligenceSection;
