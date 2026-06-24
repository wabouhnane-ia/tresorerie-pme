import { useEffect, useState } from "react";
import { analyticsService } from "../services/analyticsService";
import { useTranslation } from "../i18n/LanguageProvider";

export default function SubscriptionCard() {
  const { t } = useTranslation();
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsService
      .getSubscription()
      .then(setSubscription)
      .catch(() => setSubscription(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100 text-sm text-gray-400">
        {t("subscription.loadingPlan")}
      </div>
    );
  }

  if (!subscription) return null;

  const plan = subscription.plan || {};
  const usage = subscription.usage || {};
  const isPremium = plan.code === "premium" || subscription.role === "super_admin";

  return (
    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100">
      <h3 className="text-lg font-bold text-gray-800 mb-4">{t("subscription.yourPlan")}</h3>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="text-sm text-gray-500">{t("subscription.currentPlan")}</p>
          <p className="text-xl font-semibold text-gray-900">
            {plan.name || t("subscription.freeTrial")}
          </p>
          {subscription.status && (
            <p className="text-sm text-gray-500 mt-1 capitalize">{subscription.status}</p>
          )}
        </div>
        <div className="grid grid-cols-2 gap-4 text-center">
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-2xl font-bold text-gray-800">{usage.uploads_used ?? 0}</p>
            <p className="text-xs text-gray-500 mt-1">{t("common.uploads")}</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-2xl font-bold text-gray-800">{usage.total_forecast_runs ?? 0}</p>
            <p className="text-xs text-gray-500 mt-1">{t("subscription.forecasts")}</p>
          </div>
        </div>
      </div>
      {!isPremium && plan.max_uploads != null && (
        <p className="text-sm text-amber-700 mt-4">
          {t("subscription.trialLimit", {
            used: usage.uploads_used ?? 0,
            max: plan.max_uploads,
          })}
        </p>
      )}
    </div>
  );
}
