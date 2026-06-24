import { useEffect, useState } from "react";
import API from "../services/api";
import { useTranslation } from "../i18n/LanguageProvider";
import { formatDateTime } from "../utils/localeFormat";

export default function AdminSubscriptionsPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersRes, analyticsRes] = await Promise.all([
        API.get("/admin/users-subscriptions"),
        API.get("/admin/subscription-analytics"),
      ]);
      setUsers(usersRes.data.users || []);
      setAnalytics(analyticsRes.data);
    } catch (err) {
      console.error(err);
      setError(t("admin.loadError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">{t("admin.title")}</h1>
        <p className="text-gray-600">{t("admin.subtitle")}</p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">{error}</div>
      )}

      {analytics && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">{t("admin.analyticsTitle")}</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: t("admin.trial"), value: analytics.trial_subscriptions, color: "amber" },
              { label: t("admin.active"), value: analytics.active_subscriptions, color: "emerald" },
              { label: t("admin.expired"), value: analytics.expired_subscriptions, color: "red" },
              { label: t("admin.mrr"), value: analytics.mrr, color: "blue" },
              { label: t("admin.arr"), value: analytics.arr, color: "indigo" },
            ].map((card) => (
              <div
                key={card.label}
                className="bg-white rounded-xl border border-gray-100 shadow-sm p-4"
              >
                <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">{t("admin.loading")}</div>
      ) : (
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{t("admin.colUser")}</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{t("admin.colRole")}</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{t("admin.colPlan")}</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{t("admin.colUploads")}</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{t("admin.colForecasts")}</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{t("admin.colCreated")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.map((u) => (
                <tr key={u.user_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{u.email}</div>
                    <div className="text-sm text-gray-500">
                      {u.first_name} {u.last_name}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">{u.role}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${
                        u.plan_code === "premium"
                          ? "bg-green-100 text-green-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {u.plan_code}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">{u.total_uploads}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{u.total_forecast_runs}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDateTime(u.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="text-center py-12 text-gray-500">{t("admin.noUsers")}</div>
          )}
        </div>
      )}
    </div>
  );
}
