export function formatDate(dateStr, options = {}) {
  if (!dateStr) return "—";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "—";
    const hasPresetStyle = options.dateStyle || options.timeStyle;
    const baseOptions = hasPresetStyle
      ? options
      : { day: "numeric", month: "long", year: "numeric", ...options };
    const locale = navigator.language || "fr-FR";
    return new Intl.DateTimeFormat(locale, baseOptions).format(date);
  } catch {
    return String(dateStr);
  }
}

export function formatDateRange(dateRange) {
  if (!dateRange || !dateRange.min_date || !dateRange.max_date) return "—";
  return `${formatDate(dateRange.min_date)} → ${formatDate(dateRange.max_date)}`;
}
