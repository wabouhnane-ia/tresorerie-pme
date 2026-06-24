import { useTranslation } from "../i18n/LanguageProvider";

export default function UpgradeBanner({ show, onUpgrade, loading = false }) {
  const { t } = useTranslation();
  if (!show) return null;

  return (
    <div className="w-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl shadow-lg p-5 flex flex-col md:flex-row items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center text-2xl">
          🔒
        </div>
        <div>
          <p className="text-white font-bold text-base leading-tight">{t("subscription.trialUsedTitle")}</p>
          <p className="text-amber-100 text-sm mt-0.5">{t("subscription.trialUsedBody")}</p>
        </div>
      </div>

      <button
        type="button"
        onClick={onUpgrade}
        disabled={loading}
        className="flex-shrink-0 flex items-center gap-2 px-6 py-3 bg-white text-amber-700 font-bold rounded-xl hover:bg-amber-50 transition-all duration-200 shadow-md disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <span className="animate-spin text-lg">⏳</span>
            <span>{t("subscription.activating")}</span>
          </>
        ) : (
          <>
            <span>⭐</span>
            <span>{t("subscription.upgradeCta")}</span>
          </>
        )}
      </button>
    </div>
  );
}
