#!/usr/bin/env python3

# Test script to isolate the ra_instructions formatting issue

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from task_manager.ra_instructions import RAInstructionsManager
    print("✓ Successfully imported RAInstructionsManager")
    
    manager = RAInstructionsManager()
    print("✓ Successfully created RAInstructionsManager instance")
    
    instructions = manager.get_full_instructions()
    print("✓ Successfully got full instructions")
    print("Instructions length:", len(instructions))
    
except Exception as e:
    print("✗ Error:", str(e))
    import traceback
    traceback.print_exc()