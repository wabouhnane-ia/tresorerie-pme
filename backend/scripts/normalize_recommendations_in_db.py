import os
import json
from pymongo import MongoClient

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
MONGODB_URL = None
MONGODB_DB = None
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k == 'MONGODB_URL':
                MONGODB_URL = v
            if k == 'MONGODB_DB':
                MONGODB_DB = v

if not MONGODB_URL or not MONGODB_DB:
    print(json.dumps({'error': 'Missing MONGODB_URL or MONGODB_DB in .env'}))
    raise SystemExit(1)

client = MongoClient(MONGODB_URL)
db = client[MONGODB_DB]
col = db['recommendations']

severity_map = {
    'critical': 'Critique', 'critique': 'Critique', 'CRITICAL': 'Critique',
    'high': 'Élevé', 'élevé': 'Élevé', 'HIGH': 'Élevé',
    'medium': 'Moyen', 'moyen': 'Moyen', 'MEDIUM': 'Moyen',
    'low': 'Faible', 'faible': 'Faible', 'LOW': 'Faible',
}

difficulty_map = {
    'easy': 'Facile', 'facile': 'Facile',
    'medium': 'Moyen', 'moyen': 'Moyen',
    'hard': 'Difficile', 'difficile': 'Difficile',
}


def normalize_time_horizon(th: str) -> str:
    if not isinstance(th, str):
        return th
    t = th
    t = t.replace('days', 'jours').replace('day', 'jours')
    t = t.replace('Next', 'Prochains')
    t = t.replace('next', 'Prochains')
    return t


count = 0
for doc in col.find({}):
    modified = False
    items = doc.get('recommendations', {}).get('items', [])
    for itm in items:
        # severity
        sev = itm.get('severity')
        if isinstance(sev, str):
            mapped = severity_map.get(sev.strip(), None)
            if not mapped:
                mapped = severity_map.get(sev.strip().lower(), None)
            if mapped and mapped != sev:
                itm['severity'] = mapped
                modified = True
        # difficulty
        diff = itm.get('difficulty')
        if isinstance(diff, str):
            mapped = difficulty_map.get(diff.strip().lower())
            if mapped and mapped != diff:
                itm['difficulty'] = mapped
                modified = True
        # time_horizon
        th = itm.get('time_horizon')
        new_th = normalize_time_horizon(th)
        if new_th != th:
            itm['time_horizon'] = new_th
            modified = True
    # metadata language
    meta = doc.get('metadata', {})
    if meta.get('language') != 'fr':
        meta['language'] = 'fr'
        doc['metadata'] = meta
        modified = True
    if modified:
        col.update_one({'_id': doc['_id']}, {'$set': {'recommendations.items': items, 'metadata': doc['metadata']}})
        count += 1

print(json.dumps({'updated_documents': count}))
