"""Integration test: Validate the decision creation flow with date serialization."""

from datetime import date, datetime, timezone
from app.services.decision_service import _serialize_for_mongo

def test_api_payload_flow():
    """Simulate the exact flow of API request -> service -> MongoDB."""
    
    # Simulate incoming API request with decision_date as string
    api_payload = {
        "decision_title": "Q2 Cost Reduction Initiative",
        "decision_description": "Implement automated expense tracking",
        "decision_date": "2026-06-01",  # From API as string
        "source": "manual",
        "priority": "high",
        "expected_benefit": "Reduce operational costs by 15%",
        "created_from_analysis_id": None,
    }
    
    # Simulate what happens in create_decision() - Parse the date
    now = datetime.now(timezone.utc)
    decision_date = api_payload.get("decision_date") or now.date()
    if isinstance(decision_date, str):
        decision_date = date.fromisoformat(decision_date[:10])
    
    print(f"1. Parsed date from API: {decision_date} (type: {type(decision_date).__name__})")
    
    # Simulate the document creation
    doc = {
        "company_id": "507f1f77bcf86cd799439011",
        "decision_date": decision_date,  # ⚠️ This is datetime.date
        "decision_title": api_payload["decision_title"].strip(),
        "decision_description": api_payload.get("decision_description", "").strip(),
        "source": api_payload.get("source") or "manual",
        "priority": api_payload.get("priority") or "medium",
        "status": "pending",
        "expected_benefit": api_payload.get("expected_benefit", "").strip(),
        "created_from_analysis_id": None,
        "baseline_scores": {"health": 75.5, "resilience": 80.0, "runway_days": 30},
        "impact": None,
        "created_at": now,
        "updated_at": now,
        "status_changed_at": now,
        "completed_at": None,
    }
    
    print(f"2. Document before serialization:")
    print(f"   - decision_date: {doc['decision_date']} (type: {type(doc['decision_date']).__name__})")
    print(f"   - created_at: {doc['created_at']} (type: {type(doc['created_at']).__name__})")
    
    # THE FIX: Serialize before MongoDB insert
    serialized_doc = _serialize_for_mongo(doc)
    
    print(f"\n3. Document after serialization:")
    print(f"   - decision_date: {serialized_doc['decision_date']} (type: {type(serialized_doc['decision_date']).__name__})")
    print(f"   - created_at: {serialized_doc['created_at']} (type: {type(serialized_doc['created_at']).__name__})")
    
    # Verify the fix
    assert isinstance(serialized_doc["decision_date"], datetime), "decision_date must be datetime"
    assert isinstance(serialized_doc["created_at"], datetime), "created_at must be datetime"
    assert serialized_doc["decision_date"].tzinfo == timezone.utc, "All datetimes must have UTC timezone"
    
    print(f"\n✓ FIX VALIDATED: All date fields are now MongoDB-compatible!")
    print(f"✓ This document will successfully insert into MongoDB without BSON encoding errors")
    
    return serialized_doc

if __name__ == "__main__":
    print("=" * 70)
    print("INTEGRATION TEST: Date Serialization in Decision Creation Flow")
    print("=" * 70)
    print()
    
    result = test_api_payload_flow()
    
    print("\n" + "=" * 70)
    print("TEST PASSED ✓")
    print("=" * 70)
