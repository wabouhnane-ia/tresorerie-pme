import asyncio
import os
import sys
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from app.utils.bson_utils import ObjectId
from app.db.mongodb import database
from app.db import collections as c
from app.auth.jwt_handler import create_access_token


def create_test_user_and_company():
    # Insert company
    company = {
        "_id": ObjectId(),
        "name": "Runtime Validation Company",
    }
    loop = asyncio.get_event_loop()
    from pymongo.errors import DuplicateKeyError

    try:
        loop.run_until_complete(database[c.COMPANIES].insert_one(company))
    except DuplicateKeyError:
        # Company already exists; try to find it
        existing = loop.run_until_complete(database[c.COMPANIES].find_one({"name": company["name"]}))
        if existing:
            company["_id"] = existing["_id"]

    # Insert user (handle duplicate email by retrieving existing user)
    user = {
        "_id": ObjectId(),
        "email": "runtime@local",
        "first_name": "Runtime",
        "last_name": "Validator",
        "company_id": company["_id"],
        "created_at": None
    }
    try:
        loop.run_until_complete(database[c.USERS].insert_one(user))
    except DuplicateKeyError:
        existing_user = loop.run_until_complete(database[c.USERS].find_one({"email": user["email"]}))
        if existing_user:
            user["_id"] = existing_user["_id"]

    return str(user["_id"]), str(company["_id"])


def generate_token(user_id: str, company_id: str):
    payload = {"sub": user_id, "company_id": company_id}
    token = create_access_token(payload)
    return token


def upload_file(token: str, filepath: str):
    url = "http://127.0.0.1:8000/upload/financial-data"
    headers = {"Authorization": f"Bearer {token}"}
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "text/csv")}
        data = {"locale": "fr"}
        resp = requests.post(url, headers=headers, files=files, data=data)
    try:
        print("Status:", resp.status_code)
        print(resp.json())
    except Exception:
        print(resp.text)


if __name__ == '__main__':
    user_id, company_id = create_test_user_and_company()
    token = generate_token(user_id, company_id)
    csv_path = os.path.join(str(Path(__file__).parent), "..", "test_datasets", "treasury_3_years_historical_dataset.csv")
    csv_path = os.path.abspath(csv_path)
    upload_file(token, csv_path)
