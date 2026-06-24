RISK_RULES = {

    "low": [

        "Maintain current financial strategy",

        "Consider moderate business expansion",

        "Monitor cashflow regularly"
    ],

    "medium": [

        "Reduce non-essential expenses",

        "Increase invoice collection efforts",

        "Monitor supplier payments carefully",

        "Strengthen short-term liquidity"
    ],

    "high": [

        "Urgently reduce operational expenses",

        "Request short-term financing",

        "Delay non-critical investments",

        "Accelerate unpaid invoice recovery",

        "Activate financial crisis management"
    ]
}


# ---------------------------------
# Alert rules
# ---------------------------------

ALERT_RULES = {

    "low": {

        "title":
            "System Stable",

        "message":
            "Treasury situation is healthy.",

        "color":
            "green"
    },

    "medium": {

        "title":
            "Liquidity Warning",

        "message":
            "Cashflow pressure increasing.",

        "color":
            "yellow"
    },

    "high": {

        "title":
            "Critical Financial Risk",

        "message":
            "Immediate financial intervention required.",

        "color":
            "red"
    }
}