import { Languages } from "lucide-react";
import { useTranslation } from "@/i18n/LanguageProvider";

export function LanguageSelector() {
  const { language, languages, setLanguage, t } = useTranslation();

  return (
    <label className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-2 py-1 text-sm text-foreground">
      <Languages className="h-4 w-4 text-muted-foreground" />
      <span className="sr-only">{t("common.language")}</span>
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value)}
        className="bg-transparent text-sm outline-none"
        aria-label={t("common.language")}
      >
        {languages.map((item) => (
          <option key={item.code} value={item.code}>
            {item.nativeLabel}
          </option>
        ))}
      </select>
    </label>
  );
}
