"""Test to validate datetime.date -> datetime.datetime serialization for MongoDB."""

from datetime import date, datetime, timezone
from app.services.decision_service import _serialize_for_mongo

def test_serialize_date_to_datetime():
    """Verify that datetime.date is converted to datetime.datetime."""
    today = date.today()
    result = _serialize_for_mongo(today)
    
    assert isinstance(result, datetime), f"Expected datetime, got {type(result)}"
    assert result.tzinfo == timezone.utc, f"Expected UTC timezone, got {result.tzinfo}"
    assert result.hour == 0 and result.minute == 0 and result.second == 0
    print(f"✓ Single date conversion: {today} -> {result}")

def test_serialize_dict_with_dates():
    """Verify nested date fields in dictionaries are converted."""
    doc = {
        "decision_date": date(2026, 6, 1),
        "created_at": datetime(2026, 6, 3, 10, 30, tzinfo=timezone.utc),
        "completed_at": None,
        "nested": {
            "inner_date": date(2026, 1, 15),
        },
    }
    
    result = _serialize_for_mongo(doc)
    
    # Check decision_date was converted
    assert isinstance(result["decision_date"], datetime), "decision_date should be datetime"
    assert result["decision_date"].tzinfo == timezone.utc
    assert result["decision_date"].date() == date(2026, 6, 1)
    
    # Check created_at remains datetime
    assert isinstance(result["created_at"], datetime), "created_at should remain datetime"
    assert result["created_at"] == datetime(2026, 6, 3, 10, 30, tzinfo=timezone.utc)
    
    # Check completed_at remains None
    assert result["completed_at"] is None
    
    # Check nested date was converted
    assert isinstance(result["nested"]["inner_date"], datetime), "nested date should be converted"
    assert result["nested"]["inner_date"].date() == date(2026, 1, 15)
    
    print(f"✓ Dict with nested dates: conversion successful")

def test_serialize_list_with_dates():
    """Verify date fields in lists are converted."""
    doc = [
        date(2026, 6, 1),
        datetime(2026, 6, 3, 10, 30, tzinfo=timezone.utc),
        "string_value",
    ]
    
    result = _serialize_for_mongo(doc)
    
    assert isinstance(result[0], datetime), "First list item should be datetime"
    assert result[0].date() == date(2026, 6, 1)
    assert isinstance(result[1], datetime)
    assert result[2] == "string_value"
    
    print(f"✓ List with dates: conversion successful")

def test_serialize_complex_document():
    """Simulate the actual decision document structure."""
    doc = {
        "company_id": "507f1f77bcf86cd799439011",
        "decision_date": date(2026, 6, 1),  # This was causing the error
        "decision_title": "Test Decision",
        "decision_description": "Description",
        "source": "manual",
        "priority": "medium",
        "status": "pending",
        "expected_benefit": "Some benefit",
        "created_from_analysis_id": None,
        "baseline_scores": {
            "health": 75.5,
            "resilience": 80.0,
            "runway_days": 30,
        },
        "impact": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "status_changed_at": datetime.now(timezone.utc),
        "completed_at": None,
    }
    
    result = _serialize_for_mongo(doc)
    
    # Verify decision_date was converted to datetime
    assert isinstance(result["decision_date"], datetime), "decision_date should be datetime"
    assert result["decision_date"].tzinfo == timezone.utc
    assert result["decision_date"].date() == date(2026, 6, 1)
    
    # All other datetime fields should remain datetime
    for field in ["created_at", "updated_at", "status_changed_at"]:
        assert isinstance(result[field], datetime), f"{field} should be datetime"
    
    # Verify completed_at remains None
    assert result["completed_at"] is None
    
    print(f"✓ Complex document (decision): conversion successful")

if __name__ == "__main__":
    print("Running date serialization tests...\n")
    test_serialize_date_to_datetime()
    test_serialize_dict_with_dates()
    test_serialize_list_with_dates()
    test_serialize_complex_document()
    print("\n✓ All tests passed! The fix is working correctly.")
