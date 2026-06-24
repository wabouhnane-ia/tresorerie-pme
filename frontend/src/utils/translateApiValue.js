/**
 * Maps backend API display strings to i18n keys (presentation layer only).
 */

const RISK_TITLE_MAP = {
  "Liquidity Risk": "api.risk.liquidity",
  "Cashflow Risk": "api.risk.cashflow",
  "Revenue Risk": "api.risk.revenue",
  "Expense Inflation Risk": "api.risk.expenseInflation",
  "Volatility Risk": "api.risk.volatility",
  "Forecast Deterioration Risk": "api.risk.forecastDeterioration",
};

const HEALTH_LABEL_PATTERNS = [
  { match: /excellente|excellent/i, key: "api.health.excellent" },
  { match: /bonne|good|healthy/i, key: "api.health.healthy" },
  { match: /vigilance|caution/i, key: "api.health.vigilance" },
  { match: /fragile/i, key: "api.health.fragile" },
  { match: /critique|critical/i, key: "api.health.critical" },
];

const RESILIENCE_PATTERNS = [
  { match: /très forte|very strong/i, key: "api.resilience.veryStrong" },
  { match: /^forte$|^strong$/i, key: "api.resilience.strong" },
  { match: /modérée|moderate/i, key: "api.resilience.moderate" },
  { match: /faible|weak/i, key: "api.resilience.weak" },
  { match: /critique|critical/i, key: "api.resilience.critical" },
];

function normalizeKey(value) {
  return String(value || "").trim().toLowerCase();
}

export function translateSeverity(value, t) {
  const k = normalizeKey(value);
  const key = `api.severity.${k}`;
  const translated = t(key);
  return translated !== key ? translated : value;
}

const URGENCY_PHRASE_MAP = {
  "within 30 days": "api.urgency.within30Days",
  "within 15 days": "api.urgency.within15Days",
  "within 7 days": "api.urgency.within7Days",
  "monitor monthly": "api.urgency.monitorMonthly",
  "sous 30 jours": "api.urgency.within30Days",
  "sous 15 jours": "api.urgency.within15Days",
  "sous 7 jours": "api.urgency.within7Days",
  "suivi mensuel": "api.urgency.monitorMonthly",
};

export function translateUrgency(value, t) {
  const k = normalizeKey(value);
  const phraseKey = URGENCY_PHRASE_MAP[k];
  if (phraseKey) {
    const translated = t(phraseKey);
    if (translated !== phraseKey) return translated;
  }
  const key = `api.urgency.${k}`;
  const translated = t(key);
  return translated !== key ? translated : value;
}

export function translateProbability(value, t) {
  const k = normalizeKey(value);
  const key = `api.probability.${k}`;
  const translated = t(key);
  return translated !== key ? translated : value;
}

export function translateRiskTitle(value, t) {
  if (!value) return value;
  const key = RISK_TITLE_MAP[value];
  if (key) return t(key);
  return value;
}

export function translateHealthLabel(value, t) {
  if (!value) return t("common.notAvailable");
  for (const { match, key } of HEALTH_LABEL_PATTERNS) {
    if (match.test(value)) return t(key);
  }
  return value;
}

export function translateResilienceLabel(value, t) {
  if (!value) return t("common.notAvailable");
  for (const { match, key } of RESILIENCE_PATTERNS) {
    if (match.test(value)) return t(key);
  }
  return value;
}

export function translateRunwayLevel(value, t) {
  const k = normalizeKey(value);
  const key = `api.runway.${k}`;
  const translated = t(key);
  return translated !== key ? translated : value;
}

/** Long narrative text from API — returned as-is (backend content). */
export function translateApiNarrative(value) {
  return value ?? "";
}
