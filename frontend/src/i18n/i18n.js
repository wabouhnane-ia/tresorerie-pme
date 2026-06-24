import fr from "./fr.json";
import en from "./en.json";
import ar from "./ar.json";

export const STORAGE_KEY = "tresorerie_locale";
export const DEFAULT_LANGUAGE = "fr";

export const SUPPORTED_LANGUAGES = {
  fr: { code: "fr", label: "Français", nativeLabel: "Français", dir: "ltr", locale: "fr-FR" },
  en: { code: "en", label: "English", nativeLabel: "English", dir: "ltr", locale: "en-GB" },
  ar: { code: "ar", label: "Arabic", nativeLabel: "العربية", dir: "rtl", locale: "ar-MA" },
};

const bundles = { fr, en, ar };

export function isSupportedLanguage(code) {
  return Boolean(code && SUPPORTED_LANGUAGES[code]);
}

export function normalizeLanguage(code) {
  if (!code || typeof code !== "string") return DEFAULT_LANGUAGE;
  const normalized = code.toLowerCase().split(/[-_]/)[0];
  return isSupportedLanguage(normalized) ? normalized : DEFAULT_LANGUAGE;
}

export function getStoredLanguage() {
  if (typeof window === "undefined") return DEFAULT_LANGUAGE;
  try {
    return normalizeLanguage(localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_LANGUAGE;
  }
}

export function persistLanguage(code) {
  const language = normalizeLanguage(code);
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(STORAGE_KEY, language);
    } catch {
      /* ignore */
    }
  }
  return language;
}

function getNested(obj, path) {
  return path.split(".").reduce((acc, part) => {
    if (acc && typeof acc === "object" && part in acc) return acc[part];
    return undefined;
  }, obj);
}

export function translate(language, key, vars = {}) {
  const lang = normalizeLanguage(language);
  let text = getNested(bundles[lang], key);
  if (text === undefined && lang !== DEFAULT_LANGUAGE) {
    text = getNested(bundles[DEFAULT_LANGUAGE], key);
  }
  if (typeof text !== "string") return key;

  return text.replace(/\{\{(\w+)\}\}/g, (_, name) => {
    const val = vars[name];
    return val !== undefined && val !== null ? String(val) : "";
  });
}

export function getLanguageMeta(language = DEFAULT_LANGUAGE) {
  return SUPPORTED_LANGUAGES[normalizeLanguage(language)];
}

export function getLocaleTag(language = DEFAULT_LANGUAGE) {
  return getLanguageMeta(language).locale;
}
