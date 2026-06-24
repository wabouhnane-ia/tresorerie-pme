#!/usr/bin/env python
"""Verify notifications are in the database."""

import requests
import json

# Your token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YTE0NDQyMjJhMjlhNTUzMjA3NWRlODIiLCJlbWFpbCI6InRlc3RfcHJlbWl1bV8yMDI2MDUyNV8xMzQ0MTdAZXhhbXBsZS5jb20iLCJjb21wYW55X2lkIjoiNmExNDQ0MjIyYTI5YTU1MzIwNzVkZTgzIiwiZXhwIjoxNzgwNDkyMTE0fQ.9C0GiX_WNWSbAxZaNRgILASd1L1rsZVvQ66xYk1mejE"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("=" * 70)
print("📋 VERIFYING NOTIFICATIONS IN DATABASE")
print("=" * 70)
print()

try:
    # Get unread count
    print("1️⃣  Getting unread notifications...")
    response = requests.get(
        "http://localhost:8000/notifications/unread",
        headers=headers
    )
    unread_data = response.json()
    print(f"   ✅ Unread count: {unread_data.get('unread_count', 0)}")
    print(f"   Critical: {unread_data.get('critical_count', 0)}")
    print()

    # Get statistics
    print("2️⃣  Getting statistics...")
    response = requests.get(
        "http://localhost:8000/notifications/statistics",
        headers=headers
    )
    stats = response.json()
    print(f"   Total: {stats.get('total_count', 0)}")
    print(f"   By type:")
    for notif_type, count in stats.get('by_type', {}).items():
        print(f"      - {notif_type}: {count}")
    print(f"   By severity:")
    for severity, count in stats.get('by_severity', {}).items():
        print(f"      - {severity}: {count}")
    print()

    # Get all notifications
    print("3️⃣  Getting all notifications (first 10)...")
    response = requests.get(
        "http://localhost:8000/notifications?limit=10&skip=0",
        headers=headers
    )
    data = response.json()
    notifications = data.get('notifications', [])
    print(f"   Total in database: {data.get('total', 0)}")
    print(f"   Showing: {len(notifications)}")
    print()
    
    for i, notif in enumerate(notifications[:10], 1):
        icon_map = {
            'warning': '⚠️',
            'risk': '🔴',
            'opportunity': '🟢',
            'decision': '📋',
            'success': '✅',
        }
        icon = icon_map.get(notif.get('type'), '📬')
        
        read_status = "✓ Read" if notif.get('is_read') else "● Unread"
        
        print(f"   {i}. {icon} [{notif.get('severity').upper()}] {read_status}")
        print(f"      {notif.get('title')}")
        print(f"      {notif.get('message')[:50]}...")
        print()

    print("=" * 70)
    print("✅ Database verification complete!")
    print("=" * 70)
    print()
    print("🌐 Open frontend: http://localhost:5173")
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")
