/**
 * DEPRECATED: These functions use static locale.
 * Use formatters from useTranslation() hook instead for proper i18n support.
 * 
 * Migration guide:
 * const { formatDate, formatCurrency, formatNumber } = useTranslation();
 * formatCurrency(amount, 'MAD') - instead of formatMad()
 * formatDate(date, options) - instead of formatDate()
 * formatNumber(value, options) - instead of raw toLocaleString()
 */

import { getLocaleTag, getStoredLanguage } from "../i18n/i18n";

// Get current locale dynamically (not cached at module load)
function getCurrentLocaleTag() {
  const currentLang = getStoredLanguage();
  return getLocaleTag(currentLang);
}

export function formatDateTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString(getCurrentLocaleTag(), {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return String(value);
  }
}

export function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString(getCurrentLocaleTag(), {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return String(value);
  }
}

export function formatMad(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Number(value).toLocaleString(getCurrentLocaleTag(), {
    maximumFractionDigits: 0,
  })} MAD`;
}

export function formatMadCompact(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const numeric = Number(value);
  const localeTag = getCurrentLocaleTag();
  
  if (Math.abs(numeric) >= 1000000) {
    return `${(numeric / 1000000).toLocaleString(localeTag, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })} M MAD`;
  }
  if (Math.abs(numeric) >= 1000) {
    return `${(numeric / 1000).toLocaleString(localeTag, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    })} K MAD`;
  }
  return formatMad(numeric);
}
