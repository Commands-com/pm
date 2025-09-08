#!/usr/bin/env python3

# Simple test to check the specific JSON string formatting

# Test the same pattern that's causing issues
test_string = f"""
PARAMETER FORMATS (CRITICAL):
- ra_metadata: JSON string of object (e.g., '{{"key": "value", "estimated_hours": 16}}')
"""

print("✓ String formatting works!")
print("Test string:", repr(test_string))