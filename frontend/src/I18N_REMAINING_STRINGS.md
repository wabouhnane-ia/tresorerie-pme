# i18n audit — remaining hardcoded / non-localized content

Sprint scope: **application 100 % française** (une seule locale `fr`). Les fichiers `en.json` / `ar.json` et le sélecteur de langue ont été retirés.

## Intentionally not localized (by design)

| Source | Examples | Reason |
|--------|----------|--------|
| **Backend API narratives** | `executive_summary`, `financial_situation`, alert `description`, risk `recommended_action`, resilience `drivers`, health `explanation` | Generated/stored server-side (often French or English prose). UI shows them as returned. |
| **Backend upload error messages** | `response.data.message`, `detail.message` from `/upload/financial-data` | Upload engine messages; UI maps **error codes** to i18n titles but still displays the API `message` body. |
| **Auth API errors** | FastAPI `detail` strings on login/register | Returned from backend validation/auth. |
| **PDF report** | `backend/app/reporting/pdf_report.py` | Separate French executive PDF pipeline; not tied to UI locale selector. |
| **PDF download filename** | `treasury-intelligence-executif-YYYY-MM-DD.pdf` | Fixed product filename. |

## Dynamic / user data (never translated)

- User names (`first_name`, `last_name`)
- Company name, sector, city (user input)
- Email addresses
- Upload filenames (`original_filename`)
- Plan names from API when not matching catalog keys (`subscription.plan.name`)
- Subscription `status` field (e.g. `active`) — shown as API value
- Admin: `role`, `plan_code` codes (`free_trial`, `premium`, `super_admin`)
- Numeric amounts, MAD values, dates in API payloads
- BI `as_of_date` string from API (not re-formatted)
- Column names in upload error lists (`missing_columns`)

## Partially localized (enum mapping only)

| Field | UI behavior |
|-------|-------------|
| Severity (`Critical`, `High`, …) | Mapped via `api.severity.*` when value matches known keys |
| Urgency / probability | Same via `api.urgency.*`, `api.probability.*` |
| Risk titles (6 English titles) | Mapped via `api.risk.*` |
| Health / resilience **labels** | Pattern-matched to `api.health.*` / `api.resilience.*` |
| Other API labels | Shown verbatim if no mapping |

## UI chrome without translation keys

| Location | String | Notes |
|----------|--------|-------|
| Score cards | `/100` | Universal numeric suffix |
| Recharts | Internal series name uses `forecast.subtitle` | Axis/tooltip localized |
| Emoji icons | 🏦 📊 🔒 etc. | Universal |
| File sizes | `KB`, `MB` | SI units |
| Modal close | `✕` | Symbol |
| Notification bell | No label (icon only) | — |

## Console / dev-only

- `console.warn` / `console.error` messages in services and layout (English)

## Components audited (migrated to `useTranslation`)

- `App.jsx` — `LanguageProvider`, placeholder routes
- `layouts/DashboardLayout.jsx` — nav, header, language selector, subscription sidebar
- `pages/DashboardPage.jsx`
- `pages/LoginPage.jsx` (+ language selector on auth screen)
- `pages/ReportsPage.jsx`
- `pages/UploadsPage.jsx`
- `pages/AdminSubscriptionsPage.jsx`
- `components/BusinessIntelligenceSection.jsx`
- `components/UploadZone.jsx`
- `components/ForecastChart.jsx`
- `components/OnboardingStatusCard.jsx`
- `components/UpgradeBanner.jsx`
- `components/SubscriptionCard.jsx`
- `components/LanguageSelector.jsx`

## Infrastructure

| File | Role |
|------|------|
| `frontend/src/i18n/fr.json` | French catalog |
| `frontend/src/i18n/en.json` | English catalog |
| `frontend/src/i18n/ar.json` | Arabic catalog |
| `frontend/src/i18n/i18n.js` | Bundles, `translate()`, `localStorage` key `tresorerie_locale` |
| `frontend/src/i18n/LanguageProvider.jsx` | Context, `html[lang]`, `html[dir]` for RTL |
| `frontend/src/utils/localeFormat.js` | `formatDateTime`, `formatMad`, `formatMadCompact` |
| `frontend/src/utils/translateApiValue.js` | API enum → i18n keys |
| `frontend/src/index.css` | Basic RTL text alignment helpers |

## Follow-ups (out of sprint scope)

1. Pass `Accept-Language` or `locale` query param to backend for localized API narratives and upload errors.
2. Wire PDF generation to UI locale (or keep French-only PDF as product rule).
3. Translate `plan.name` via server-side catalog or frontend map (`free_trial` → key).
4. Mobile sidebar menu (hamburger) — still hidden on desktop; labels not duplicated for mobile drawer.
5. Expand `translateApiValue` for French backend strings (drivers, opportunity titles).
