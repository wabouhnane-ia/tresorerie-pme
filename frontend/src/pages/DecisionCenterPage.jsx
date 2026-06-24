
import { useEffect, useState } from "react";
import API from "../services/api";
import { ensureArray, safeGet } from "../utils/safeDataAccess";
import { useTranslation } from "../i18n/LanguageProvider";
import DecisionCenterSection from "../components/DecisionCenterSection";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

export default function DecisionCenterPage() {
  const { t, language } = useTranslation();
  const [businessIntelligence, setBusinessIntelligence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBusinessIntelligence();
  }, [language]);

  const fetchBusinessIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await API.get("/analytics/latest-analysis");
      setBusinessIntelligence(safeGet(res.data, "business_intelligence", null));
    } catch (err) {
      console.error("Failed to fetch business intelligence:", err);
      setError(t("dashboard.loadError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("decisions.sectionTitle")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t("decisions.sectionSubtitle")}
        </p>
      </div>

      {loading && (
        <div className="py-8 text-center text-sm text-muted-foreground">
          {t("dashboard.loadingData")}
        </div>
      )}

      {error && (
        <div className="py-8 text-center text-sm text-destructive">
          {error}
        </div>
      )}

      {!loading && !error && (
        <DecisionCenterSection businessIntelligence={businessIntelligence} />
      )}
    </div>
  );
}
