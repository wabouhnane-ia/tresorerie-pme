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

doc = col.find_one(sort=[('metadata.generated_at', -1)])
if not doc:
    print(json.dumps({'error': 'No recommendation documents found'}))
else:
    out = {}
    out['_id'] = str(doc.get('_id'))
    out['metadata_language'] = doc.get('metadata', {}).get('language')
    out['metadata'] = doc.get('metadata')
    out['executive_analysis_present'] = bool(doc.get('executive_analysis'))
    recs = doc.get('recommendations', {}).get('items', [])
    out['recommendation_count'] = len(recs)
    out['sample_recommendations'] = recs[:3]
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
