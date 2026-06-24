"""
Safe BSON utilities with fallback for environments without pymongo/bson.
"""

# Safe import of ObjectId with fallback
try:
    from bson.objectid import ObjectId
except (ImportError, ModuleNotFoundError):
    try:
        from bson import ObjectId
    except (ImportError, ModuleNotFoundError):
        # Fallback for environments without bson
        class ObjectId:
            """Fallback ObjectId for environments without bson."""
            def __init__(self, oid):
                self.oid = str(oid)
            
            def __str__(self):
                return self.oid
            
            def __repr__(self):
                return f"ObjectId('{self.oid}')"
            
            def __eq__(self, other):
                if isinstance(other, ObjectId):
                    return self.oid == other.oid
                return self.oid == str(other)
            
            def __hash__(self):
                return hash(self.oid)

__all__ = ['ObjectId']
