import time
import json
import pandas as pd
from app.services.upload_parser import detect_columns

cases = {
    'historical_file': ('test_datasets/treasury_3_years_historical_dataset.csv', True),
    'monthly_file': ('test_datasets/TEST_MONTHLY_REJECTED.csv', True),
    'encaissements_client_paiements_fournisseurs': (['Date opération','Encaissements_Client','Paiements_Fournisseurs','Flux_Tresorerie','Solde_Bancaire'], False),
    'reglements_clients_fournisseurs': (['Date opération','Règlements Clients','Règlements Fournisseurs','Solde'], False),
    'encaissemnt_client_typo': (['Date opération','Encaissemnt Client','Charges','Solde'], False)
}

results = {}

for name, (data, is_file) in cases.items():
    if is_file:
        try:
            import csv
            with open(data, newline='', encoding='utf-8') as f:
                headers = next(csv.reader(f))
        except Exception as e:
            results[name] = {'error': f'cannot read file {data}: {e}'}
            continue
    else:
        headers = data

    df = pd.DataFrame({h: ['1'] for h in headers})
    t0 = time.perf_counter()
    mapping, report = detect_columns(df, locale='fr', return_report=True)
    t1 = time.perf_counter()
    time_ms = (t1-t0)*1000
    per = report.get('per_column', {})
    recognized = sum(1 for v in per.values() if v.get('matched_to'))
    total = len(per)
    recognition_rate = recognized/total if total else 0
    counts = {'exact':0,'canonical':0,'fuzzy':0,'none':0}
    for v in per.values():
        m = v.get('method')
        if m in counts:
            counts[m]+=1
        else:
            counts['none']+=1
    results[name] = {
        'headers': headers,
        'mapping': mapping,
        'mapping_quality_score': report.get('mapping_quality_score'),
        'time_ms': int(time_ms),
        'recognized_columns': recognized,
        'total_columns': total,
        'recognition_rate': round(recognition_rate,2),
        'counts_by_method': counts,
        'suggestions': report.get('suggestions')
    }

print(json.dumps(results, indent=2, ensure_ascii=False))
