
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { decisionService } from "../services/decisionService";
import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { getLocaleTag } from "../i18n/i18n";
import { useTranslation } from "../i18n/LanguageProvider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Activity, Banknote, CheckCircle2, Scale } from "lucide-react";

function formatMadValue(value) {
  if (value == null || value === "") return "-";
  const numeric = Number(String(value).replace(/\s/g, "").replace(/[^\d.-]/g, ""));
  if (Number.isNaN(numeric)) return String(value);
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toLocaleString(getLocaleTag(), { maximumFractionDigits: 0 })} MAD`;
}

function parseExpectedBenefit(value) {
  const text = String(value || "");
  const match = text.match(/Impact financier estimé \(MAD\):\s*([^|]+)/i);
  return match ? match[1].trim() : "";
}

export default function DecisionCenterSummary() {
  const { t } = useTranslation();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [totalFinancialImpact, setTotalFinancialImpact] = useState(0);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [decisionsRes, impactRes] = await Promise.all([
        decisionService.getDecisions(),
        decisionService.getImpact()
      ]);
      setAnalytics(impactRes);

      const allDecisions = [
        ...ensureArray(safeGet(decisionsRes, "grouped.pending", [])),
        ...ensureArray(safeGet(decisionsRes, "grouped.in_progress", [])),
        ...ensureArray(safeGet(decisionsRes, "grouped.completed", [])),
        ...ensureArray(safeGet(decisionsRes, "grouped.cancelled", [])),
      ];

      const total = allDecisions.reduce((sum, decision) => {
        const metadata = parseExpectedBenefit(decision.expected_benefit);
        const numeric = Number(String(metadata || "").replace(/\s/g, "").replace(/[^\d.-]/g, ""));
        return Number.isNaN(numeric) ? sum : sum + numeric;
      }, 0);

      setTotalFinancialImpact(total);
    } catch (err) {
      console.warn("Could not load decision summary:", err);
    } finally {
      setLoading(false);
    }
  };

  const stats = [
    {
      label: "Décisions actives",
      value: loading ? "-" : (analytics?.pending_decisions ?? 0) + (analytics?.in_progress_decisions ?? 0),
      icon: Activity,
    },
    {
      label: "Décisions réalisées",
      value: loading ? "-" : analytics?.completed_decisions ?? 0,
      icon: CheckCircle2,
    },
    {
      label: "Impact cumulé",
      value: loading ? "-" : formatMadValue(totalFinancialImpact),
      icon: Banknote,
    },
  ];

  return (
    <Card className="border-border">
      <CardHeader className="space-y-3 pb-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-muted-foreground" />
            <div>
              <CardTitle className="text-lg">{t("decisions.sectionTitle")}</CardTitle>
              <CardDescription>Aperçu rapide des décisions</CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          {stats.map(({ label, value, icon: Icon }) => (
        <Card key={label} className="border-border bg-background">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-2">
              <CardDescription className="text-xs">{label}</CardDescription>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <CardTitle className="text-xl">{value}</CardTitle>
          </CardHeader>
        </Card>
      ))}
        </div>
        <Link to="/decision-center" className="w-full">
          <Button variant="default" className="w-full" size="sm">
            Ouvrir le centre de décision
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
