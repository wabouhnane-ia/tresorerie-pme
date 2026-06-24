#!/usr/bin/env python
"""Test the POST /notifications/test endpoint."""

import requests
import json

# Your token from the login response
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YTE0NDQyMjJhMjlhNTUzMjA3NWRlODIiLCJlbWFpbCI6InRlc3RfcHJlbWl1bV8yMDI2MDUyNV8xMzQ0MTdAZXhhbXBsZS5jb20iLCJjb21wYW55X2lkIjoiNmExNDQ0MjIyYTI5YTU1MzIwNzVkZTgzIiwiZXhwIjoxNzgwNDkyMTE0fQ.9C0GiX_WNWSbAxZaNRgILASd1L1rsZVvQ66xYk1mejE"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("=" * 70)
print("🧪 TESTING POST /api/notifications/test")
print("=" * 70)

try:
    response = requests.post(
        "http://localhost:8000/notifications/test",
        headers=headers
    )
    
    print(f"\n✅ Status Code: {response.status_code}")
    print(f"\n📦 Response:")
    
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    if response.status_code == 200:
        notification_id = data.get("notification", {}).get("_id")
        company_id = data.get("notification", {}).get("company_id")
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS! Notification created:")
        print(f"   - ID: {notification_id}")
        print(f"   - Company: {company_id}")
        print(f"   - Type: {data.get('notification', {}).get('type')}")
        print(f"   - Severity: {data.get('notification', {}).get('severity')}")
        print("=" * 70)
        
        print("\n🔍 Next steps to see it in the UI:")
        print("   1. Open http://localhost:5173 in your browser")
        print("   2. The NotificationBell should show a badge with '1'")
        print("   3. Click the bell to open NotificationCenter")
        print("   4. You should see the test notification listed")
        print("   5. Try marking it as read, delete it, etc.")
        
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ Connection Error: {e}")
    print("\n📍 Make sure:")
    print("   1. Backend is running: uvicorn app.main:app --reload")
    print("   2. MongoDB is running and accessible")
    print("   3. API is on http://localhost:8000")
