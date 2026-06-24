import asyncio
from app.db.mongodb import database
from app.db import collections as c

async def main():
    col_names = [
        c.UPLOADS,
        c.FINANCIAL_RECORDS,
        c.FORECAST_RUNS,
        c.FORECASTS,
        c.RECOMMENDATIONS,
        c.DATA_QUALITY_REPORTS,
        c.RISK_ASSESSMENTS,
    ]

    results = {}
    for cn in col_names:
        try:
            results[cn] = await database[cn].count_documents({})
        except Exception as e:
            results[cn] = f"ERROR: {e}"

    for k, v in results.items():
        print(f"{k}: {v}")

if __name__ == '__main__':
    asyncio.run(main())
