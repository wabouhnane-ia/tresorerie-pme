/**
 * Safe Data Access Utilities
 */
import { getLocaleTag } from "../i18n/i18n";

export const safeGet = (obj, path, defaultValue = null) => {
  if (!obj) return defaultValue;

  const keys = path.split(".");
  let current = obj;

  for (const key of keys) {
    if (current == null) return defaultValue;
    current = current[key];
  }

  return current ?? defaultValue;
};

export const ensureArray = (data) => {
  if (Array.isArray(data)) return data;
  if (data == null) return [];
  return [data];
};

export const ensureObject = (data) => {
  if (data && typeof data === "object" && !Array.isArray(data)) return data;
  return {};
};

export const hasContent = (data) => {
  if (data == null) return false;
  if (Array.isArray(data)) return data.length > 0;
  if (typeof data === "object") return Object.keys(data).length > 0;
  if (typeof data === "string") return data.trim().length > 0;
  return Boolean(data);
};

export const formatCurrency = (value, locale = getLocaleTag(), currency = "MAD") => {
  if (value == null || Number.isNaN(Number(value))) return "—";

  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: currency,
      maximumFractionDigits: 0,
    }).format(Number(value));
  } catch {
    return "—";
  }
};

export const formatPercent = (value) => {
  if (value == null || Number.isNaN(Number(value))) return "—";

  try {
    return `${(Number(value) * 100).toFixed(0)} %`;
  } catch {
    return "—";
  }
};

export const formatDate = (dateStr, locale = getLocaleTag()) => {
  if (!dateStr) return "—";

  try {
    const date = new Date(dateStr);
    if (Number.isNaN(date.valueOf())) return "—";
    return date.toLocaleString(locale);
  } catch {
    return "—";
  }
};
