import { useCallback, useEffect, useState } from "react";
import { notificationService } from "../services/notificationService";
import { useNotificationShell } from "../contexts/NotificationShellContext";
import { decisionService } from "../services/decisionService";
import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { getLocaleTag } from "../i18n/i18n";
import { useTranslation } from "../i18n/LanguageProvider";
import { formatDate } from "../utils/localeFormat";
import DecisionTimeline from "./DecisionTimeline";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select } from "./ui/select";
import { Separator } from "./ui/separator";
import { Textarea } from "./ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "./ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { ScrollArea } from "./ui/scroll-area";
import {
  Activity,
  Banknote,
  CheckCircle2,
  Clock,
  FileText,
  LineChart,
  ShieldCheck,
  Target,
} from "lucide-react";

const DECISION_CATEGORIES = [
  { value: "cash_optimization", labelKey: "decisions.category.cashOptimization" },
  { value: "customer_collections", labelKey: "decisions.category.customerCollections" },
  { value: "supplier_payments", labelKey: "decisions.category.supplierPayments" },
  { value: "bank_financing", labelKey: "decisions.category.bankFinancing" },
  { value: "cost_reduction", labelKey: "decisions.category.costReduction" },
  { value: "investment", labelKey: "decisions.category.investment" },
  { value: "other", labelKey: "decisions.category.other" },
];

const DECISION_SOURCE_OPTIONS = [
  { value: "manual", apiValue: "manual", labelKey: "decisions.formSource.manual" },
  { value: "business_intelligence", apiValue: "dashboard", labelKey: "decisions.formSource.businessIntelligence" },
  { value: "notification", apiValue: "dashboard", labelKey: "decisions.formSource.notification" },
  { value: "forecast", apiValue: "dashboard", labelKey: "decisions.formSource.forecast" },
];

const DECISION_PRIORITIES = ["low", "medium", "high", "critical"];

const PRIORITY_LABELS = {
  critical: "Critique",
  high: "Élevée",
  medium: "Moyenne",
  low: "Faible",
};

const SOURCE_LABELS = {
  manual: "Manuelle",
  dashboard: "Business Intelligence",
  executive_pdf: "Rapport exécutif",
};

const initialDecisionForm = {
  decision_title: "",
  decision_description: "",
  category: "",
  estimated_financial_impact: "",
  priority: "",
  owner: "",
  target_date: "",
  decision_source: "manual",
};

const emptyRecommendationDraft = {
  decision_title: "",
  decision_description: "",
  category: "",
  estimated_financial_impact: "",
  priority: "",
  owner: "",
  target_date: "",
  decision_source: "manual",
};

function formatMadValue(value) {
  if (value == null || value === "") return "-";
  const numeric = Number(String(value).replace(/\s/g, "").replace(/[^\d.-]/g, ""));
  if (Number.isNaN(numeric)) return String(value);
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toLocaleString(getLocaleTag(), { maximumFractionDigits: 0 })} MAD`;
}

function formatSignedValue(value, suffix) {
  if (value == null || Number.isNaN(Number(value))) return null;
  const numeric = Number(value);
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toLocaleString(getLocaleTag(), { maximumFractionDigits: 1 })} ${suffix}`;
}

function parseExpectedBenefit(value) {
  const text = String(value || "");
  const readField = (label) => {
    const match = text.match(new RegExp(`${label}:\\s*([^|]+)`, "i"));
    return match ? match[1].trim() : "";
  };

  return {
    category: readField("Catégorie"),
    estimatedImpact: readField("Impact financier estimé \\(MAD\\)").replace(/\s*MAD$/i, ""),
    owner: readField("Responsable"),
    targetDate: readField("Date cible"),
    decisionSource: readField("Source de la décision"),
  };
}

function inferPriority(value) {
  const text = String(value || "").toLowerCase();
  if (["critical", "critique", "immediate", "immédiat"].some((item) => text.includes(item))) return "critical";
  if (["high", "élevée", "elevee", "urgent"].some((item) => text.includes(item))) return "high";
  if (["low", "faible"].some((item) => text.includes(item))) return "low";
  return "medium";
}

function inferCategory(text) {
  const value = String(text || "").toLowerCase();
  if (value.includes("client") || value.includes("encaissement")) return "customer_collections";
  if (value.includes("fournisseur") || value.includes("paiement")) return "supplier_payments";
  if (value.includes("banque") || value.includes("financement")) return "bank_financing";
  if (value.includes("coût") || value.includes("cout") || value.includes("charge")) return "cost_reduction";
  if (value.includes("invest")) return "investment";
  if (value.includes("trésorerie") || value.includes("tresorerie") || value.includes("cash")) return "cash_optimization";
  return "other";
}

function firstNonEmpty(...values) {
  return values.find((value) => value != null && String(value).trim() !== "") || "";
}

const getStatusVariant = (status) => {
  if (status === "completed") return "default";
  if (status === "in_progress") return "secondary";
  if (status === "cancelled") return "outline";
  return "secondary";
};

const getPriorityVariant = (priority) => {
  if (priority === "critical" || priority === "high") return "destructive";
  if (priority === "medium") return "secondary";
  return "outline";
};

function ImpactBadges({ impact }) {
  const { t } = useTranslation();
  if (!impact) return null;

  const items = [
    { key: "health", value: impact.health_delta, label: t("decisions.impactHealth") },
    { key: "resilience", value: impact.resilience_delta, label: t("decisions.impactResilience") },
    { key: "runway", value: impact.runway_delta, label: t("decisions.impactRunway"), suffix: t("common.days") },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {items.map(({ key, value, label, suffix }) => {
        const num = Number(value) ?? 0;
        const sign = num > 0 ? "+" : "";
        const variant = num > 0 ? "default" : num < 0 ? "destructive" : "secondary";
        return (
          <Badge key={key} variant={variant} className="text-xs">
            {label}: {sign}{num}{suffix ? ` ${suffix}` : ""}
          </Badge>
        );
      })}
    </div>
  );
}

function ObservedImpactBlock({ decision }) {
  const impact = decision.impact;

  const items = [
    { label: "Variation du runway", value: formatSignedValue(impact?.runway_delta, "jours") },
    { label: "Variation résilience", value: formatSignedValue(impact?.resilience_delta, "points") },
    { label: "Variation santé financière", value: formatSignedValue(impact?.health_delta, "points") },
  ]

  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <p className="mb-3 text-sm font-medium">Impact observé</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {items.map((item) => (
          <div key={item.label}>
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-sm font-semibold">{item.value ?? "0"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionCard({ decision, onStatusChange, updating }) {
  const { t } = useTranslation();
  const status = decision.status || "pending";
  const metadata = parseExpectedBenefit(decision.expected_benefit);
  const estimatedImpact = metadata.estimatedImpact;
  const owner = metadata.owner;
  const targetDate = metadata.targetDate;
  const source = metadata.decisionSource || SOURCE_LABELS[decision.source] || decision.source || "-";
  const priority = decision.priority || "medium";

  return (
    <Card className="border-border bg-card">
      <CardHeader className="space-y-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 space-y-1">
            <p className="text-xs text-muted-foreground">{formatDate(decision.decision_date)}</p>
            <CardTitle className="text-base font-semibold leading-snug">
              {decision.decision_title}
            </CardTitle>
          </div>
          <Badge variant={getStatusVariant(status)} className="text-xs shrink-0">
            {t(`decisions.status.${status}`)}
          </Badge>
        </div>
        
        {decision.decision_description && (
          <CardDescription className="text-xs line-clamp-2">
            {decision.decision_description}
          </CardDescription>
        )}

        <div className="grid gap-3 text-xs sm:grid-cols-2 xl:grid-cols-5">
          <div>
            <p className="text-muted-foreground">Impact estimé</p>
            <p className="font-semibold">{estimatedImpact ? formatMadValue(estimatedImpact) : "-"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Responsable</p>
            <p className="font-semibold">{owner || "-"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Date cible</p>
            <p className="font-semibold">{targetDate || "-"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Source</p>
            <p className="font-semibold">{source}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Priorité</p>
            <Badge variant={getPriorityVariant(priority)} className="mt-1 text-xs">
              {t(`decisions.priority.${priority}`)}
            </Badge>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {metadata.category && (
            <Badge variant="secondary" className="text-xs">
              {metadata.category}
            </Badge>
          )}
          <Badge variant={getPriorityVariant(priority)} className="text-xs">
            Niveau de priorité: {PRIORITY_LABELS[priority] || t(`decisions.priority.${priority}`)}
          </Badge>
        </div>
      </CardHeader>

      {decision.impact && (
        <CardContent className="pb-3 pt-0">
          <ImpactBadges impact={decision.impact} />
        </CardContent>
      )}

      {status !== "completed" && status !== "cancelled" && (
        <CardContent className="pt-0">
          <Separator className="mb-3" />
          <div className="flex flex-wrap gap-2">
            {status === "pending" && (
              <Button
                variant="default"
                size="sm"
                disabled={updating}
                onClick={() => onStatusChange(decision.id, "in_progress")}
              >
                {t("decisions.markInProgress")}
              </Button>
            )}
            {status === "in_progress" && (
              <Button
                variant="default"
                size="sm"
                disabled={updating}
                onClick={() => onStatusChange(decision.id, "completed")}
              >
                {t("decisions.markCompleted")}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              disabled={updating}
              onClick={() => onStatusChange(decision.id, "cancelled")}
            >
              {t("decisions.cancel")}
            </Button>
          </div>
        </CardContent>
      )}

      {status === "completed" && (
        <CardContent className="pt-0">
          <Separator className="mb-3" />
          <ObservedImpactBlock decision={decision} />
        </CardContent>
      )}
    </Card>
  );
}

function AnalyticsBar({ analytics, totalFinancialImpact }) {
  if (!analytics) return null;

  const averageDeltas = analytics.average_impact_deltas || {};
  const stats = [
    {
      label: "Décisions actives",
      value: (analytics.pending_decisions ?? 0) + (analytics.in_progress_decisions ?? 0),
      icon: Activity,
    },
    {
      label: "Impact financier cumulé",
      value: totalFinancialImpact == null ? "-" : formatMadValue(totalFinancialImpact),
      icon: Banknote,
    },
    {
      label: "Décisions réalisées",
      value: analytics.completed_decisions ?? 0,
      icon: CheckCircle2,
    },
    {
      label: "Taux d'exécution",
      value: `${analytics.execution_rate ?? 0}%`,
      icon: Target,
    },
    {
      label: "Impact observé sur le runway",
      value: formatSignedValue(averageDeltas.runway_delta, "jours") || "Impact en cours d'évaluation",
      icon: LineChart,
    },
    {
      label: "Impact observé sur la résilience",
      value: formatSignedValue(averageDeltas.resilience_delta, "points") || "Impact en cours d'évaluation",
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {stats.map(({ label, value, icon: Icon }) => (
        <Card key={label} className="border-border bg-card">
          <CardHeader className="space-y-3 pb-4">
            <div className="flex items-center justify-between gap-3">
              <CardDescription className="text-xs uppercase tracking-wide">{label}</CardDescription>
              <div className="rounded-md border border-border bg-background p-2">
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
            <CardTitle className="text-2xl font-semibold tracking-tight">{value}</CardTitle>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}

function buildRecommendations(intelligence) {
  if (!intelligence) return [];

  const briefing = intelligence.executive_briefing || {};
  const recommendedDecision = safeGet(briefing, "recommended_decision", {});
  const mainRisk = safeGet(briefing, "main_risk", {});
  const alerts = ensureArray(intelligence.smart_alerts);
  const risks = ensureArray(intelligence.top_risks);
  const decisions = ensureArray(intelligence.top_decisions);
  const recommendations = [];

  if (safeGet(recommendedDecision, "action")) {
    recommendations.push({
      id: "briefing-recommended-decision",
      title: safeGet(recommendedDecision, "action"),
      estimatedImpact: firstNonEmpty(
        safeGet(recommendedDecision, "expected_outcome"),
        safeGet(recommendedDecision, "expected_benefit")
      ),
      urgency: safeGet(recommendedDecision, "urgency", "medium"),
      source: "Executive briefing",
      justification: firstNonEmpty(
        safeGet(recommendedDecision, "rationale"),
        safeGet(briefing, "executive_summary")
      ),
      category: inferCategory(safeGet(recommendedDecision, "action")),
    });
  }

  if (safeGet(mainRisk, "recommended_action")) {
    recommendations.push({
      id: "briefing-main-risk",
      title: safeGet(mainRisk, "recommended_action"),
      estimatedImpact: safeGet(mainRisk, "estimated_financial_impact"),
      urgency: safeGet(mainRisk, "severity", "high"),
      source: "Executive briefing",
      justification: firstNonEmpty(safeGet(mainRisk, "description"), safeGet(mainRisk, "title")),
      category: inferCategory(`${safeGet(mainRisk, "title")} ${safeGet(mainRisk, "recommended_action")}`),
    });
  }

  alerts.slice(0, 3).forEach((alert, index) => {
    if (!safeGet(alert, "recommended_action")) return;
    recommendations.push({
      id: `alert-${index}`,
      title: safeGet(alert, "recommended_action"),
      estimatedImpact: safeGet(alert, "business_impact"),
      urgency: safeGet(alert, "severity", "medium"),
      source: "Notification",
      justification: firstNonEmpty(safeGet(alert, "description"), safeGet(alert, "title")),
      category: inferCategory(`${safeGet(alert, "title")} ${safeGet(alert, "recommended_action")}`),
    });
  });

  risks.slice(0, 3).forEach((risk, index) => {
    if (!safeGet(risk, "recommended_action")) return;
    recommendations.push({
      id: `risk-${index}`,
      title: safeGet(risk, "recommended_action"),
      estimatedImpact: safeGet(risk, "estimated_financial_impact"),
      urgency: firstNonEmpty(safeGet(risk, "urgency"), safeGet(risk, "severity")),
      source: "Top risks",
      justification: firstNonEmpty(safeGet(risk, "description"), safeGet(risk, "title")),
      category: inferCategory(`${safeGet(risk, "title")} ${safeGet(risk, "recommended_action")}`),
    });
  });

  decisions.slice(0, 3).forEach((decision, index) => {
    if (!safeGet(decision, "action")) return;
    recommendations.push({
      id: `decision-${index}`,
      title: safeGet(decision, "action"),
      estimatedImpact: firstNonEmpty(
        safeGet(decision, "estimated_financial_impact"),
        safeGet(decision, "expected_benefit")
      ),
      urgency: safeGet(decision, "urgency", "medium"),
      source: "Top decisions",
      justification: firstNonEmpty(
        safeGet(decision, "business_justification"),
        safeGet(decision, "why"),
        safeGet(decision, "expected_benefit")
      ),
      category: inferCategory(safeGet(decision, "action")),
    });
  });

  const seen = new Set();
  return recommendations.filter((item) => {
    const key = String(item.title || "").toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function RecommendationCard({ recommendation, onCreate }) {
  const { t } = useTranslation();
  const priority = inferPriority(recommendation.urgency);

  return (
    <Card className="border-border bg-muted/20">
      <CardHeader className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base leading-snug">{recommendation.title}</CardTitle>
            <CardDescription>{recommendation.justification || t("decisions.justificationUnavailable")}</CardDescription>
          </div>
          <Badge variant={getPriorityVariant(priority)}>{PRIORITY_LABELS[priority]}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 text-sm md:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">{t("decisions.estimatedImpact")}</p>
            <p className="font-medium">{recommendation.estimatedImpact || "-"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("decisions.urgency")}</p>
            <p className="font-medium">{recommendation.urgency || "-"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("decisions.sourceLabel")}</p>
            <p className="font-medium">{recommendation.source}</p>
          </div>
        </div>
        <Button type="button" size="sm" onClick={() => onCreate(recommendation)}>
          {t("decisions.createDecision")}
        </Button>
      </CardContent>
    </Card>
  );
}

function RecommendedDecisionsSection({ recommendations, onCreate }) {
  const { t } = useTranslation();

  if (!recommendations.length) {
    return (
      <Alert>
        <FileText className="h-4 w-4" />
        <AlertTitle>{t("decisions.recommendedTitle")}</AlertTitle>
        <AlertDescription>
          {t("decisions.noBiRecommendation")}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="text-xl">{t("decisions.recommendedTitle")}</CardTitle>
        <CardDescription>
          {t("decisions.recommendedSubtitle")}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 xl:grid-cols-2">
        {recommendations.map((recommendation) => (
          <RecommendationCard
            key={recommendation.id}
            recommendation={recommendation}
            onCreate={onCreate}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function DecisionRegister({ active, completed, cancelled, onStatusChange, updatingId }) {
  const { t } = useTranslation();

  const renderList = (items, emptyLabel) => (
    <ScrollArea className="h-[560px] pr-3">
      <div className="space-y-3">
        {items.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-8 text-center">
              <p className="text-sm text-muted-foreground">{emptyLabel}</p>
            </CardContent>
          </Card>
        ) : (
          items.map((decision) => (
            <DecisionCard
              key={decision.id}
              decision={decision}
              onStatusChange={onStatusChange}
              updating={updatingId === decision.id}
            />
          ))
        )}
      </div>
    </ScrollArea>
  );

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="text-xl">Registre décisionnel</CardTitle>
        <CardDescription>
          Suivi des décisions financières, de leur statut et de leur contribution observée.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="active">
          <TabsList>
            <TabsTrigger value="active">Actives ({active.length})</TabsTrigger>
            <TabsTrigger value="completed">Réalisées ({completed.length})</TabsTrigger>
            <TabsTrigger value="cancelled">Annulées ({cancelled.length})</TabsTrigger>
          </TabsList>
          <TabsContent value="active" className="pt-4">
            {renderList(active, t("decisions.noPending"))}
          </TabsContent>
          <TabsContent value="completed" className="pt-4">
            {renderList(completed, t("decisions.noCompleted"))}
          </TabsContent>
          <TabsContent value="cancelled" className="pt-4">
            {renderList(cancelled, "Aucune décision annulée")}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function ObservedImpactSection({ completed }) {
  const withImpact = completed.filter((decision) => decision.impact);

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="text-xl">Impact observé</CardTitle>
        <CardDescription>
          Effets mesurés après réalisation des décisions, lorsque les données sont disponibles.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {completed.length === 0 ? (
          <Alert>
            <Clock className="h-4 w-4" />
            <AlertTitle>Aucune décision réalisée</AlertTitle>
            <AlertDescription>Impact en cours d'évaluation</AlertDescription>
          </Alert>
        ) : withImpact.length === 0 ? (
          <Alert>
            <Clock className="h-4 w-4" />
            <AlertTitle>Impact en cours d'évaluation</AlertTitle>
            <AlertDescription>
              Les variations de runway, résilience et santé financière seront affichées dès qu'elles seront disponibles.
            </AlertDescription>
          </Alert>
        ) : (
          withImpact.map((decision) => (
            <Card key={decision.id} className="border-border bg-muted/20">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">{decision.decision_title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <ObservedImpactBlock decision={decision} />
              </CardContent>
            </Card>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function CreateDecisionForm({ open, onOpenChange, onCreated, prefill }) {
  const { t } = useTranslation();
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [form, setForm] = useState({ ...initialDecisionForm, ...(prefill || {}) });

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const validate = () => {
    const nextErrors = {};
    if (!form.decision_title.trim()) {
      nextErrors.decision_title = t("decisions.validation.titleRequired");
    }
    if (!form.category) {
      nextErrors.category = t("decisions.validation.categoryRequired");
    }
    if (!form.priority) {
      nextErrors.priority = t("decisions.validation.priorityRequired");
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const getLabel = (options, value) => {
    const option = options.find((item) => item.value === value);
    return option ? t(option.labelKey) : "";
  };

  const buildExpectedBenefit = () => {
    const parts = [
      `${t("decisions.categoryLabel")}: ${getLabel(DECISION_CATEGORIES, form.category)}`,
    ];

    if (form.estimated_financial_impact) {
      parts.push(`${t("decisions.estimatedFinancialImpact")}: ${form.estimated_financial_impact} MAD`);
    }
    if (form.owner.trim()) {
      parts.push(`${t("decisions.owner")}: ${form.owner.trim()}`);
    }
    if (form.target_date) {
      parts.push(`${t("decisions.targetDate")}: ${form.target_date}`);
    }
    parts.push(`${t("decisions.decisionSource")}: ${getLabel(DECISION_SOURCE_OPTIONS, form.decision_source)}`);

    return parts.join(" | ");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    const sourceOption = DECISION_SOURCE_OPTIONS.find((item) => item.value === form.decision_source);
    setSubmitting(true);
    try {
      await decisionService.createDecision({
        decision_title: form.decision_title.trim(),
        decision_description: form.decision_description.trim(),
        decision_date: form.target_date || undefined,
        source: sourceOption?.apiValue || "manual",
        priority: form.priority,
        expected_benefit: buildExpectedBenefit(),
      });
      setForm(initialDecisionForm);
      setErrors({});
      onOpenChange(false);
      onCreated();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-hidden sm:max-w-xl">
        <SheetHeader className="border-b">
          <SheetTitle>{t("decisions.newDecision")}</SheetTitle>
          <SheetDescription>{t("decisions.formSubtitle")}</SheetDescription>
        </SheetHeader>
        <ScrollArea className="min-h-0 flex-1 px-4 pb-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-sm font-medium" htmlFor="decision-title">
                {t("decisions.titleLabel")} *
              </label>
              <Input
                id="decision-title"
                aria-invalid={!!errors.decision_title}
                placeholder={t("decisions.titlePlaceholder")}
                value={form.decision_title}
                onChange={(e) => updateField("decision_title", e.target.value)}
              />
              {errors.decision_title && (
                <p className="text-xs text-destructive">{errors.decision_title}</p>
              )}
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <label className="text-sm font-medium" htmlFor="decision-description">
                {t("decisions.descriptionLabel")}
              </label>
              <Textarea
                id="decision-description"
                placeholder={t("decisions.descriptionPlaceholder")}
                value={form.decision_description}
                onChange={(e) => updateField("decision_description", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="decision-category">
                {t("decisions.categoryLabel")} *
              </label>
              <Select
                id="decision-category"
                aria-invalid={!!errors.category}
                value={form.category}
                onChange={(e) => updateField("category", e.target.value)}
              >
                <option value="">{t("decisions.selectPlaceholder")}</option>
                {DECISION_CATEGORIES.map((category) => (
                  <option key={category.value} value={category.value}>
                    {t(category.labelKey)}
                  </option>
                ))}
              </Select>
              {errors.category && (
                <p className="text-xs text-destructive">{errors.category}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="decision-impact">
                {t("decisions.estimatedFinancialImpact")}
              </label>
              <Input
                id="decision-impact"
                inputMode="numeric"
                placeholder="0"
                value={form.estimated_financial_impact}
                onChange={(e) => updateField("estimated_financial_impact", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="decision-priority">
                {t("decisions.priorityLabel")} *
              </label>
              <Select
                id="decision-priority"
                aria-invalid={!!errors.priority}
                value={form.priority}
                onChange={(e) => updateField("priority", e.target.value)}
              >
                <option value="">{t("decisions.selectPlaceholder")}</option>
                {DECISION_PRIORITIES.map((priority) => (
                  <option key={priority} value={priority}>
                    {t(`decisions.priority.${priority}`)}
                  </option>
                ))}
              </Select>
              {errors.priority && (
                <p className="text-xs text-destructive">{errors.priority}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="decision-owner">
                {t("decisions.owner")}
              </label>
              <Input
                id="decision-owner"
                placeholder={t("decisions.ownerPlaceholder")}
                value={form.owner}
                onChange={(e) => updateField("owner", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="decision-target-date">
                {t("decisions.targetDate")}
              </label>
              <Input
                id="decision-target-date"
                type="date"
                value={form.target_date}
                onChange={(e) => updateField("target_date", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="decision-source">
                {t("decisions.decisionSource")}
              </label>
              <Select
                id="decision-source"
                value={form.decision_source}
                onChange={(e) => updateField("decision_source", e.target.value)}
              >
                {DECISION_SOURCE_OPTIONS.map((source) => (
                  <option key={source.value} value={source.value}>
                    {t(source.labelKey)}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={submitting}>
              {submitting ? t("common.loading") : t("decisions.save")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                onOpenChange(false);
                setErrors({});
              }}
            >
              {t("decisions.cancelForm")}
            </Button>
          </div>
        </form>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

export default function DecisionCenterSection({ businessIntelligence }) {
  const { t } = useTranslation();
  const [grouped, setGrouped] = useState({});
  const [analytics, setAnalytics] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formPrefill, setFormPrefill] = useState(emptyRecommendationDraft);
  const { openNotificationCenter } = useNotificationShell();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [decisionsRes, impactRes, historyRes] = await Promise.all([
        decisionService.getDecisions(),
        decisionService.getImpact(),
        decisionService.getHistory(),
      ]);
      setGrouped(safeGet(decisionsRes, "grouped", {}));
      setAnalytics(impactRes);
      setHistory(historyRes);
    } catch (err) {
      console.warn("Could not load decision center:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadData();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  const handleStatusChange = async (decisionId, status) => {
    setUpdatingId(decisionId);
    try {
      await decisionService.updateStatus(decisionId, status);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleRecomputeImpact = async () => {
    try {
      const result = await decisionService.recomputeImpact();
      await notificationService.createNotification({
        notification_type: 'success',
        severity: 'low',
        title: `Impact recomputed for ${result.updated} decision(s)`,
        message: 'Decisions impact recomputed successfully.',
      });
      openNotificationCenter && openNotificationCenter();
      await loadData();
    } catch (err) {
      console.error(err);
      await notificationService.createNotification({
        notification_type: 'warning',
        severity: 'high',
        title: 'Failed to recompute impact',
        message: err?.message || String(err) || 'Recompute failed',
      });
      openNotificationCenter && openNotificationCenter();
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">{t("decisions.loading")}</p>
        </CardContent>
      </Card>
    );
  }

  const pending = ensureArray(grouped.pending);
  const inProgress = ensureArray(grouped.in_progress);
  const completed = ensureArray(grouped.completed);
  const cancelled = ensureArray(grouped.cancelled);
  const active = [...pending, ...inProgress];
  const recommendations = buildRecommendations(businessIntelligence);
  const allDecisions = [...active, ...completed, ...cancelled];
  const totalFinancialImpact = allDecisions.reduce((sum, decision) => {
    const metadata = parseExpectedBenefit(decision.expected_benefit);
    const numeric = Number(String(metadata.estimatedImpact || "").replace(/\s/g, "").replace(/[^\d.-]/g, ""));
    return Number.isNaN(numeric) ? sum : sum + numeric;
  }, 0);

  const openManualForm = () => {
    setFormPrefill(emptyRecommendationDraft);
    setFormOpen(true);
  };

  const openRecommendationForm = (recommendation) => {
    setFormPrefill({
      ...emptyRecommendationDraft,
      decision_title: recommendation.title || "",
      decision_description: recommendation.justification || "",
      category: recommendation.category || inferCategory(recommendation.title),
      estimated_financial_impact: recommendation.estimatedImpact || "",
      priority: inferPriority(recommendation.urgency),
      decision_source: recommendation.source === "Notification" ? "notification" : "business_intelligence",
    });
    setFormOpen(true);
  };

  return (
    <section className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-2xl">{t("decisions.sectionTitle")}</CardTitle>
              <CardDescription>{t("decisions.sectionSubtitle")}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button type="button" size="sm" variant="secondary" onClick={handleRecomputeImpact}>
                Recalculer impact
              </Button>
              <Button type="button" size="sm" onClick={openManualForm}>
                {t("decisions.newDecision")}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <AnalyticsBar analytics={analytics} totalFinancialImpact={allDecisions.length ? totalFinancialImpact : null} />

      <RecommendedDecisionsSection
        recommendations={recommendations}
        onCreate={openRecommendationForm}
      />

      <DecisionRegister
        active={active}
        completed={completed}
        cancelled={cancelled}
        onStatusChange={handleStatusChange}
        updatingId={updatingId}
      />

      <ObservedImpactSection completed={completed} />

      <DecisionTimeline history={history} />

      {formOpen && (
        <CreateDecisionForm
          open={formOpen}
          onOpenChange={setFormOpen}
          onCreated={loadData}
          prefill={formPrefill}
        />
      )}
    </section>
  );
}
