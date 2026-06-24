"""Simple syntax checker for migration files."""

import ast
import sys
from pathlib import Path

files_to_check = [
    "backend/app/api/analytics.py",
    "backend/app/api/companies.py",
    "backend/app/services/billing_service.py",
    "backend/app/services/plan_service.py",
    "backend/app/db/collections.py",
    "backend/app/db/init_indexes.py",
    "backend/app/db/seed.py",
    "backend/scripts/reset_db.py",
]

print("\n" + "="*70)
print("SYNTAX CHECK — Migration Files")
print("="*70 + "\n")

all_passed = True

for file_path in files_to_check:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✅ {file_path}")
    except SyntaxError as e:
        print(f"❌ {file_path}")
        print(f"   Error: {e}")
        all_passed = False
    except FileNotFoundError:
        print(f"⚠️  {file_path} (not found)")

print("\n" + "="*70)
if all_passed:
    print("✅ ALL SYNTAX CHECKS PASSED")
else:
    print("❌ SOME SYNTAX CHECKS FAILED")
print("="*70 + "\n")

sys.exit(0 if all_passed else 1)
