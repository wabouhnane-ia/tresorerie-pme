import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import {
  DEFAULT_LANGUAGE,
  getLanguageMeta,
  getLocaleTag,
  getStoredLanguage,
  normalizeLanguage,
  persistLanguage,
  SUPPORTED_LANGUAGES,
  translate,
} from "./i18n";

// Create a simple store to avoid hydration mismatch
function createLanguageStore() {
  let listeners = new Set();
  let currentLanguage = (() => {
    if (typeof window === "undefined") return DEFAULT_LANGUAGE;
    return getStoredLanguage();
  })();

  return {
    get: () => currentLanguage,
    set: (nextLanguage) => {
      const normalized = normalizeLanguage(nextLanguage);
      if (normalized !== currentLanguage) {
        currentLanguage = normalized;
        listeners.forEach((l) => l());
      }
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

const languageStore = createLanguageStore();

const LanguageContext = createContext(null);

function emptyValue(value) {
  return value === undefined || value === null || Number.isNaN(Number(value));
}

export function LanguageProvider({ children }) {
  const language = useSyncExternalStore(
    languageStore.subscribe,
    languageStore.get,
    () => DEFAULT_LANGUAGE
  );
  const meta = getLanguageMeta(language);
  const locale = getLocaleTag(language);

  useEffect(() => {
    persistLanguage(language);
    const root = document.documentElement;
    root.setAttribute("lang", language);
    root.setAttribute("dir", meta.dir);
  }, [language, meta.dir]);

  const value = useMemo(() => {
    const setLanguage = (nextLanguage) => {
      languageStore.set(nextLanguage);
    };

    const formatNumber = (valueToFormat, options = {}) => {
      if (emptyValue(valueToFormat)) return "—";
      return new Intl.NumberFormat(locale, options).format(Number(valueToFormat));
    };

    const formatCurrency = (valueToFormat, currency = "MAD", options = {}) => {
      if (emptyValue(valueToFormat)) return "—";
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
        ...options,
      }).format(Number(valueToFormat));
    };

    const formatPercent = (valueToFormat, options = {}) => {
      if (emptyValue(valueToFormat)) return "—";
      return new Intl.NumberFormat(locale, {
        style: "percent",
        maximumFractionDigits: 1,
        ...options,
      }).format(Number(valueToFormat));
    };

    const formatDate = (valueToFormat, options = {}) => {
      if (!valueToFormat) return "—";
      try {
        const hasPresetStyle = options.dateStyle || options.timeStyle;
        const baseOptions = hasPresetStyle
          ? options
          : { day: "numeric", month: "long", year: "numeric", ...options };
        return new Intl.DateTimeFormat(locale, baseOptions).format(new Date(valueToFormat));
      } catch {
        return String(valueToFormat);
      }
    };

    return {
      language,
      locale,
      dir: meta.dir,
      isRtl: meta.dir === "rtl",
      languages: Object.values(SUPPORTED_LANGUAGES),
      setLanguage,
      t: (key, vars) => translate(language, key, vars),
      formatNumber,
      formatCurrency,
      formatPercent,
      formatDate,
    };
  }, [language, locale, meta.dir]);

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export function useTranslation() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    return {
      language: DEFAULT_LANGUAGE,
      locale: getLocaleTag(DEFAULT_LANGUAGE),
      dir: "ltr",
      isRtl: false,
      languages: Object.values(SUPPORTED_LANGUAGES),
      setLanguage: () => {},
      t: (key, vars) => translate(DEFAULT_LANGUAGE, key, vars),
      formatNumber: (value) => (emptyValue(value) ? "—" : String(value)),
      formatCurrency: (value) => (emptyValue(value) ? "—" : `${value} MAD`),
      formatPercent: (value) => (emptyValue(value) ? "—" : `${value}%`),
      formatDate: (value) => (value ? String(value) : "—"),
    };
  }
  return ctx;
}
