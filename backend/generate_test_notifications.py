#!/usr/bin/env python
"""Generate multiple test notifications to test pagination and filtering."""

import requests
import json
from time import sleep

# Your token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YTE0NDQyMjJhMjlhNTUzMjA3NWRlODIiLCJlbWFpbCI6InRlc3RfcHJlbWl1bV8yMDI2MDUyNV8xMzQ0MTdAZXhhbXBsZS5jb20iLCJjb21wYW55X2lkIjoiNmExNDQ0MjIyYTI5YTU1MzIwNzVkZTgzIiwiZXhwIjoxNzgwNDkyMTE0fQ.9C0GiX_WNWSbAxZaNRgILASd1L1rsZVvQ66xYk1mejE"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

notifications = [
    {
        "type": "warning",
        "severity": "high",
        "title": "⚠️ Santé financière en baisse",
        "message": "Votre score de santé financière a baissé de 8 points cette semaine"
    },
    {
        "type": "risk",
        "severity": "critical",
        "title": "🔴 CRITIQUE: Runway < 30 jours",
        "message": "Votre horizon de trésorerie est critique. Actions recommandées: accélération des encaissements"
    },
    {
        "type": "opportunity",
        "severity": "low",
        "title": "🟢 Opportunité détectée",
        "message": "Vos délais clients offrent une opportunité d'optimisation"
    },
    {
        "type": "decision",
        "severity": "medium",
        "title": "📋 Décision en retard",
        "message": "Décision 'Refinancer dette' est en attente depuis 18 jours"
    },
    {
        "type": "warning",
        "severity": "medium",
        "title": "📊 Décaissements anormaux",
        "message": "Vos dépenses opérationnelles ont augmenté de 22% cette semaine"
    },
    {
        "type": "success",
        "severity": "low",
        "title": "✅ Décision complétée",
        "message": "Décision 'Optimiser délais fournisseurs' a été complétée avec succès"
    },
]

print("=" * 70)
print("🧪 CREATING MULTIPLE TEST NOTIFICATIONS FOR UI TESTING")
print("=" * 70)
print()

created = 0
for i, notif in enumerate(notifications, 1):
    try:
        print(f"[{i}/{len(notifications)}] Creating: {notif['title'][:40]}...", end=" ")
        
        response = requests.post(
            "http://localhost:8000/notifications/test",
            headers=headers,
            json=notif
        )
        
        if response.status_code == 200:
            print("✅")
            created += 1
            data = response.json()
            notif_id = data.get("notification", {}).get("id")
            print(f"         ID: {notif_id}")
        else:
            print(f"❌ ({response.status_code})")
            
        sleep(0.2)  # Small delay between requests
        
    except Exception as e:
        print(f"❌ Error: {e}")

print()
print("=" * 70)
print(f"✅ Created {created}/{len(notifications)} notifications")
print("=" * 70)
print()
print("🌐 Now open your browser:")
print("   → http://localhost:5173")
print()
print("You should see:")
print("   1️⃣  Notification Bell in header (top right)")
print("   2️⃣  Badge showing '{created}' unread notifications")
print("   3️⃣  Click bell → see full NotificationCenter")
print("   4️⃣  Filter by type, mark as read, delete, etc.")
print()
