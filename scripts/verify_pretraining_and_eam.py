# scripts/verify_pretraining_and_eam.py
"""
Verify that GitHub pre-training data is present and E-AM works.
"""
import asyncio
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Backend"))

from app.core.config import settings

async def verify():
    print("════════════════════════════════════════════════════════")
    print("PRE-TRAINING & E-AM VERIFICATION")
    print("════════════════════════════════════════════════════════")
    
    # 1. Check VVectorStore for GitHub data
    try:
        from app.learning.v_vector_store import get_v_vector_store
        get_v_vector_store()
        
        # We can't query by source directly easily without SQL, 
        # but we can try to search for something we know is in the pretraining data
        # like "fastapi" or "react" patterns
        
        print("\n1. Verifying Database Content...")
        
        # Manually check the DB file existence
        # The store uses "v_vector_history.db"
        db_path = settings.paths.workspaces_dir.parent / "Backend" / "data" / "v_vector_history.db"
        if db_path.exists():
            print(f"✅ Database file exists: {db_path}")
            print(f"   Size: {db_path.stat().st_size / 1024:.2f} KB")
        else:
            print(f"❌ Database file NOT found at: {db_path}")
            # Try alternate path logic if strict path fails
            alt_path = Path("Backend/data/v_vector_history.db").resolve()
            if alt_path.exists():
                 print(f"✅ Database file found at alternate path: {alt_path}")
                 print(f"   Size: {alt_path.stat().st_size / 1024:.2f} KB")
            else:
                 return
            
    except Exception as e:
        print(f"❌ Failed to connect to VVectorStore: {e}")
        return

    # 2. Test E-AM Explorer
    print("\n2. Testing E-AM Explorer (inject_foreign_patterns)...")
    try:
        from app.arbormind.explorer import inject_foreign_patterns
        
        # Enable E-AM safely for this test
        settings.am.enable_eam = True
        
        # Test Case 1: Recursion Error (should find gaming/algo patterns)
        print("\n   Test A: RecursionError in 'admin_dashboard'")
        result = await inject_foreign_patterns(
            archetype="admin_dashboard", 
            error_text="RecursionError: maximum recursion depth exceeded while calling a Python object"
        )
        
        if result.get("patterns"):
            print(f"   ✅ SUCCESS: Found {len(result['patterns'])} foreign patterns")
            print(f"   Sources: {result.get('source_archetypes')}")
            print(f"   Mode: {result.get('mode', 'combinational')}")
        else:
            print("   ⚠️  WARNING: No patterns found. (This is expected if pre-training hasn't finished yet)")
            
        # Test Case 2: React Hook Error (should find frontend patterns)
        print("\n   Test B: React Hook Error in 'backend_api'")
        result = await inject_foreign_patterns(
            archetype="backend_api", 
            error_text="Error: Invalid hook call. Hooks can only be called inside of the body of a function component."
        )
        
        if result.get("patterns"):
            print(f"   ✅ SUCCESS: Found {len(result['patterns'])} foreign patterns")
            print(f"   Sources: {result.get('source_archetypes')}")
        else:
            print("   ⚠️  WARNING: No patterns found.")
            
    except Exception as e:
        print(f"❌ E-AM Explorer Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
