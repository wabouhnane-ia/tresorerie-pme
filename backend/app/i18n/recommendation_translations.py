"""Localized recommendation copy keyed by French canonical title."""

from __future__ import annotations

# Fields translated when user locale is en or ar (canonical content is French).
RECOMMENDATION_I18N: dict[str, dict[str, dict[str, str]]] = {
    "Sécuriser la couverture de trésorerie immédiate": {
        "en": {
            "title": "Secure immediate treasury coverage",
            "why": "Treasury is projected negative in {day} days, with a potential low of {min_balance}.",
            "expected_impact": "Cover the projected shortfall of about {shortfall} and protect payroll, suppliers, and operations.",
            "description": "Confirm credit lines, accelerate major collections, and freeze non-essential payments until the gap is covered.",
            "recommended_action": "Activate a 7-day treasury protection plan with daily review.",
            "business_impact": "Avoid an operational disruption due to lack of liquidity.",
        },
        "ar": {
            "title": "تأمين تغطية السيولة الفورية",
            "why": "من المتوقع أن تصبح الخزينة سالبة خلال {day} يوماً، مع حد أدنى محتمل عند {min_balance}.",
            "expected_impact": "تغطية العجز المتوقع بحوالي {shortfall} وحماية الرواتب والموردين والعمليات.",
            "description": "تأكيد خطوط الائتمان، تسريع التحصيلات الكبرى، وتجميد المدفوعات غير الضرورية حتى سد الفجوة.",
            "recommended_action": "تفعيل خطة حماية خزينة لمدة 7 أيام مع مراجعة يومية.",
            "business_impact": "تجنب توقف تشغيلي بسبب نقص السيولة.",
        },
    },
    "Préparer un renforcement de liquidité avant tension": {
        "en": {
            "title": "Prepare liquidity reinforcement before stress",
            "why": "Treasury may turn negative in about {day} days if the trend continues.",
            "expected_impact": "Preserve operational continuity over 30 days and avoid last-minute financing.",
            "description": "Prepare a backup financing plan and prioritize collections before projected stress materializes.",
            "recommended_action": "Build a 30-day treasury bridge via collections, supplier terms, and available credit lines.",
            "business_impact": "Reduce short-term liquidity risk before it escalates.",
        },
        "ar": {
            "title": "التحضير لتعزيز السيولة قبل الضغط",
            "why": "قد تصبح الخزينة سالبة خلال نحو {day} يوماً إذا استمر الاتجاه.",
            "expected_impact": "الحفاظ على استمرارية العمليات لـ 30 يوماً وتجنب التمويل في اللحظة الأخيرة.",
            "description": "إعداد خطة تمويل احتياطية وأولوية التحصيلات قبل تحقق الضغط المتوقع.",
            "recommended_action": "بناء جسر خزينة لـ 30 يوماً عبر التحصيلات وشروط الموردين وخطوط الائتمان.",
            "business_impact": "تقليل مخاطر السيولة قصيرة الأجل قبل تفاقمها.",
        },
    },
    "Préserver les réserves de trésorerie immédiatement": {
        "en": {
            "title": "Preserve treasury reserves immediately",
            "why": "Current treasury is {balance} and recent net generation is {net_cashflow} per day.",
            "expected_impact": "Extend financial runway and keep margin to pay strategic suppliers.",
            "description": "Suspend discretionary spending, validate major payments, and keep enough cash for critical commitments.",
            "recommended_action": "Set temporary approval thresholds for non-essential outflows.",
            "business_impact": "Protect immediate operational flexibility.",
        },
        "ar": {
            "title": "الحفاظ على احتياطي الخزينة فوراً",
            "why": "الخزينة الحالية {balance} والتوليد الصافي الأخير {net_cashflow} في اليوم.",
            "expected_impact": "إطالة أفق التمويل والاحتفاظ بهامش لدفع الموردين الاستراتيجيين.",
            "description": "تعليق النفقات التقديرية، التحقق من المدفوعات الكبرى، والاحتفاظ بنقد كافٍ للالتزامات الحرجة.",
            "recommended_action": "وضع عتبات موافقة مؤقتة للصرف غير الضروري.",
            "business_impact": "حماية المرونة التشغيلية الفورية.",
        },
    },
    "Améliorer la discipline du fonds de roulement": {
        "en": {
            "title": "Improve working capital discipline",
            "why": "Current reserve is {balance} while recent daily net flow is {net_cashflow}.",
            "expected_impact": "Improve 30-day cash availability without changing the business model.",
            "description": "Shorten customer collection cycles and align supplier payments with inflows.",
            "recommended_action": "Review major overdue receivables and negotiate schedules with strategic suppliers.",
            "business_impact": "Strengthen the cash conversion cycle.",
        },
        "ar": {
            "title": "تحسين انضباط رأس المال العامل",
            "why": "الاحتياطي الحالي {balance} بينما صافي التدفق اليومي الأخير {net_cashflow}.",
            "expected_impact": "تحسين توفر النقد لـ 30 يوماً دون تغيير نموذج العمل.",
            "description": "تقصير آجال تحصيل العملاء ومواءمة مدفوعات الموردين مع التحصيلات.",
            "recommended_action": "مراجعة الذمم المتأخرة الكبرى والتفاوض على الجداول مع الموردين الاستراتيجيين.",
            "business_impact": "تعزيز دورة تحويل النقد.",
        },
    },
    "Réduire les dépenses discrétionnaires": {
        "en": {
            "title": "Reduce discretionary expenses",
            "why": "Recent net flow is negative at {net_cashflow} per day, gradually eroding treasury.",
            "expected_impact": "Slow treasury erosion and free cash for essential operations.",
            "description": "Identify non-critical spend that can be delayed, renegotiated, or cancelled this month.",
            "recommended_action": "Run a 30-day expense review focused on variable and discretionary costs.",
            "business_impact": "Reduce daily cash leakage.",
        },
        "ar": {
            "title": "خفض النفقات التقديرية",
            "why": "صافي التدفق الأخير سالب عند {net_cashflow} في اليوم، مما يآكل الخزينة تدريجياً.",
            "expected_impact": "إبطاء تآكل الخزينة وتحرير نقد للعمليات الأساسية.",
            "description": "تحديد النفقات غير الحرجة التي يمكن تأجيلها أو إعادة التفاوض عليها أو إلغاؤها هذا الشهر.",
            "recommended_action": "إطلاق مراجعة نفقات لـ 30 يوماً تركز على التكاليف المتغيرة والتقديرية.",
            "business_impact": "تقليل تسرب النقد اليومي.",
        },
    },
    "Stabiliser la visibilité des flux de trésorerie": {
        "en": {
            "title": "Stabilize cash flow visibility",
            "why": "Daily treasury movements are volatile, with swings around {volatility}.",
            "expected_impact": "Give management earlier warning of cash shortfalls or surpluses.",
            "description": "Move from monthly to weekly cash planning and isolate major movement drivers.",
            "recommended_action": "Implement a rolling 13-week view updated weekly.",
            "business_impact": "Improve predictability for management decisions.",
        },
        "ar": {
            "title": "استقرار رؤية التدفقات النقدية",
            "why": "حركات الخزينة اليومية متقلبة، بتذبذب حول {volatility}.",
            "expected_impact": "إعطاء الإدارة إنذاراً مبكراً بعجز أو فائض النقد.",
            "description": "الانتقال من التخطيط الشهري إلى الأسبوعي وعزل محركات الحركة الرئيسية.",
            "recommended_action": "اعتماد نظرة متدحرجة لـ 13 أسبوعاً تُحدَّث أسبوعياً.",
            "business_impact": "تحسين قابلية التنبؤ لقرارات الإدارة.",
        },
    },
    "Protéger les encaissements": {
        "en": {
            "title": "Protect collections",
            "why": "Treasury trajectory is declining by about {decline_rate} per day.",
            "expected_impact": "Stabilize inflows and reduce reliance on financing.",
            "description": "Prioritize confirmed collections, resolve blocked invoices, and avoid revenue loss next cycle.",
            "recommended_action": "Run a major-customer collection sprint with an owner and weekly target.",
            "business_impact": "Stop deterioration of available cash.",
        },
        "ar": {
            "title": "حماية التحصيلات",
            "why": "مسار الخزينة في تراجع بحوالي {decline_rate} في اليوم.",
            "expected_impact": "استقرار التحصيلات وتقليل الاعتماد على التمويل.",
            "description": "أولوية التحصيلات المؤكدة، حل الفواتير العالقة، وتجنب فقد الإيرادات في الدورة القادمة.",
            "recommended_action": "تنظيم سباق تحصيل للعملاء الرئيسيين مع مسؤول وهدف أسبوعي.",
            "business_impact": "وقف تدهور النقد المتاح.",
        },
    },
    "Optimiser l'allocation des excédents de trésorerie": {
        "en": {
            "title": "Optimize allocation of treasury surpluses",
            "why": "Treasury is positive at {balance} and recent cash generation is positive at {net_cashflow} per day.",
            "expected_impact": "Improve treasury yield while preserving operational liquidity.",
            "description": "Separate operating cash from surplus and define what can be invested, reserved, or used to reduce debt.",
            "recommended_action": "Set a minimum operating reserve and allocate only surplus above it.",
            "business_impact": "Monetize idle cash without weakening liquidity.",
        },
        "ar": {
            "title": "تحسين تخصيص فوائض الخزينة",
            "why": "الخزينة إيجابية عند {balance} والتوليد النقدي الأخير إيجابي عند {net_cashflow} في اليوم.",
            "expected_impact": "تحسين عائد الخزينة مع الحفاظ على سيولة التشغيل.",
            "description": "فصل النقد التشغيلي عن الفائض وتحديد ما يمكن استثماره أو حجزه أو استخدامه لسد الدين.",
            "recommended_action": "تحديد حد أدنى للاحتياطي التشغيلي وتخصيص الفائض فقط فوقه.",
            "business_impact": "استثمار النقد الراكد دون إضعاف السيولة.",
        },
    },
    "Maintenir un pilotage trésorerie hebdomadaire": {
        "en": {
            "title": "Maintain weekly treasury steering",
            "why": "Treasury is {balance} and recent net flow is {net_cashflow} per day.",
            "expected_impact": "Keep management informed and detect deterioration quickly.",
            "description": "Hold a weekly treasury review of collections, supplier payments, and upcoming commitments.",
            "recommended_action": "Review treasury position weekly with a 30-day watch list.",
            "business_impact": "Maintain financial control.",
        },
        "ar": {
            "title": "الحفاظ على قيادة خزينة أسبوعية",
            "why": "الخزينة {balance} وصافي التدفق الأخير {net_cashflow} في اليوم.",
            "expected_impact": "إبقاء الإدارة على اطلاع واكتشاف التدهور بسرعة.",
            "description": "مراجعة خزينة أسبوعية للتحصيلات ومدفوعات الموردين والالتزامات القادمة.",
            "recommended_action": "مراجعة وضع الخزينة أسبوعياً مع قائمة مراقبة لـ 30 يوماً.",
            "business_impact": "الحفاظ على السيطرة المالية.",
        },
    },
}


RISK_I18N: dict[str, dict[str, dict[str, str]]] = {
    "Risque de liquidité": {
        "en": {
            "title": "Liquidity risk",
            "description": "Risk that available treasury becomes insufficient to cover near-term operating commitments.",
            "impact": "Potential payment delays, supplier pressure, or emergency financing need.",
            "recommended_action": "Protect minimum cash reserves and prepare collection or financing levers.",
        },
        "ar": {
            "title": "مخاطر السيولة",
            "description": "خطر عدم كفاية الخزينة المتاحة لتغطية الالتزامات التشغيلية قصيرة الأجل.",
            "impact": "تأخيرات دفع أو ضغط موردين أو حاجة لتمويل طارئ.",
            "recommended_action": "حماية الحد الأدنى من النقد وإعداد روافع التحصيل أو التمويل.",
        },
    },
    "Risque de flux de trésorerie": {
        "en": {
            "title": "Cashflow risk",
            "description": "Risk that daily operations consume more cash than they generate.",
            "impact": "Treasury erosion and reduced management flexibility.",
            "recommended_action": "Improve collections and reduce non-essential outflows.",
        },
        "ar": {
            "title": "مخاطر التدفق النقدي",
            "description": "خطر أن تستهلك العمليات اليومية نقداً أكثر مما تولّد.",
            "impact": "تآكل الخزينة ومرونة إدارية أقل.",
            "recommended_action": "تحسين التحصيلات وتقليل الصرف غير الضروري.",
        },
    },
    "Risque sur les encaissements": {
        "en": {
            "title": "Revenue risk",
            "description": "Risk that incoming cash is not strong enough to support the current spending rhythm.",
            "impact": "Lower cash generation and pressure on working capital.",
            "recommended_action": "Prioritize confirmed collections and monitor top customer receipts.",
        },
        "ar": {
            "title": "مخاطر التحصيل",
            "description": "خطر أن التحصيلات لا تواكب إيقاع النفقات الحالي.",
            "impact": "انخفاض توليد النقد وضغط على رأس المال العامل.",
            "recommended_action": "أولوية التحصيلات المؤكدة ومتابعة إيصالات العملاء الرئيسيين.",
        },
    },
    "Risque d'inflation des dépenses": {
        "en": {
            "title": "Expense inflation risk",
            "description": "Risk that operating expenses rise faster than available cash generation.",
            "impact": "Margin compression and avoidable cash consumption.",
            "recommended_action": "Review discretionary expenses and renegotiate variable cost items.",
        },
        "ar": {
            "title": "مخاطر ارتفاع المصاريف",
            "description": "خطر أن ترتفع مصاريف التشغيل أسرع من توليد النقد المتاح.",
            "impact": "ضغط على الهامش واستهلاك نقد يمكن تجنبه.",
            "recommended_action": "مراجعة النفقات التقديرية وإعادة التفاوض على البنود المتغيرة.",
        },
    },
    "Risque de volatilité": {
        "en": {
            "title": "Volatility risk",
            "description": "Risk that cash movements are too irregular for reliable short-term planning.",
            "impact": "Unexpected cash gaps or idle liquidity.",
            "recommended_action": "Use a weekly rolling cash plan and track major inflow and outflow drivers.",
        },
        "ar": {
            "title": "مخاطر التقلب",
            "description": "خطر أن تكون حركات النقد غير منتظمة لتخطيط قصير الأجل موثوق.",
            "impact": "فجوات نقدية مفاجئة أو سيولة راكدة.",
            "recommended_action": "خطة نقدية متدحرجة أسبوعية ومتابعة محركات التدفق الرئيسية.",
        },
    },
    "Risque de dégradation des perspectives": {
        "en": {
            "title": "Forecast deterioration risk",
            "description": "Risk that the short-term treasury outlook continues to weaken.",
            "impact": "Reduced time to react and higher financing pressure.",
            "recommended_action": "Trigger a management review when the 30-day low balance worsens.",
        },
        "ar": {
            "title": "مخاطر تدهور الآفاق",
            "description": "خطر استمرار ضعف آفاق الخزينة قصيرة الأجل.",
            "impact": "وقت أقل للاستجابة وضغط تمويل أعلى.",
            "recommended_action": "إطلاق مراجعة إدارية عند تدهور الحد الأدنى لـ 30 يوماً.",
        },
    },
}


def localize_recommendation_item(item: dict, locale: str) -> dict:
    if locale == "fr":
        return item
    pack = RECOMMENDATION_I18N.get(item.get("title", ""), {}).get(locale)
    if not pack:
        return item
    ctx = dict(item.get("i18n_context") or {})
    out = dict(item)
    for key, template in pack.items():
        try:
            out[key] = template.format(**ctx)
        except (KeyError, ValueError):
            out[key] = template
    return out


def localize_risk_dict(risk: dict, locale: str) -> dict:
    if locale == "fr":
        return risk
    pack = RISK_I18N.get(risk.get("title", ""), {}).get(locale)
    if not pack:
        return risk
    out = dict(risk)
    out.update(pack)
    return out
