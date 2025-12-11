#!/usr/bin/env python3
"""
Verification Script: Token Policy Implementation

Tests that all fixes from Options 1, 2, and 3#7 are working correctly.
Run this to verify the implementation before testing with actual workflows.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

def test_token_policy_exists():
    """Test that token_policy.py exists and can be imported."""
    try:
        from app.orchestration.token_policy import get_tokens_for_step, STEP_TOKEN_POLICIES
        print("✅ Token policy module imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import token_policy: {e}")
        return False


def test_token_allocations():
    """Test that token allocations are correct for key steps."""
    try:
        from app.orchestration.token_policy import get_tokens_for_step
        
        tests = [
            ("analysis", False, 8000, "Analysis should get 8k tokens"),
            ("contracts", False, 8000, "Contracts should get 8k tokens"),
            ("frontend_mock", False, 12000, "Frontend Mock should get 12k tokens"),
            ("backend_implementation", False, 20000, "Backend Implementation should get 20k tokens"),
            ("backend_implementation", True, 24000, "Backend Implementation retry should get 24k tokens"),
            ("testing_backend", False, 12000, "Backend testing should get 12k tokens"),
        ]
        
        all_passed = True
        for step, is_retry, expected, description in tests:
            actual = get_tokens_for_step(step, is_retry=is_retry)
            if actual == expected:
                print(f"  ✅ {description}: {actual} tokens")
            else:
                print(f"  ❌ {description}: Expected {expected}, got {actual}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Token allocation test failed: {e}")
        return False


def test_sub_agents_uses_policy():
    """Test that sub_agents.py uses the token policy."""
    try:
        sub_agents_file = backend_path / "app" / "agents" / "sub_agents.py"
        content = sub_agents_file.read_text(encoding="utf-8")
        
        if "from app.orchestration.token_policy import get_tokens_for_step" in content:
            print("✅ sub_agents.py imports token policy")
        else:
            print("❌ sub_agents.py does NOT import token policy")
            return False
        
        if "get_tokens_for_step(step_name, is_retry=is_retry)" in content:
            print("✅ sub_agents.py uses get_tokens_for_step()")
            return True
        else:
            print("❌ sub_agents.py does NOT use get_tokens_for_step()")
            return False
            
    except Exception as e:
        print(f"❌ sub_agents.py check failed: {e}")
        return False


def test_derek_prompt_updated():
    """Test that Derek's prompt has correct token information."""
    try:
        derek_file = backend_path / "app" / "llm" / "prompts" / "derek.py"
        content = derek_file.read_text(encoding="utf-8")
        
        # Check for new token awareness section
        if "Backend Implementation: 20,000 tokens" in content:
            print("✅ Derek's prompt mentions 20k tokens for backend implementation")
        else:
            print("❌ Derek's prompt does NOT mention 20k tokens")
            return False
        
        # Check for token management guidance
        if "TOKEN MANAGEMENT (CRITICAL FOR BACKEND IMPLEMENTATION)" in content:
            print("✅ Derek's prompt has token management guidance")
            return True
        else:
            print("❌ Derek's prompt missing token management guidance")
            return False
            
    except Exception as e:
        print(f"❌ Derek prompt check failed: {e}")
        return False


def test_healing_entity_discovery():
    """Test that healing pipeline has multi-source entity discovery."""
    try:
        healing_file = backend_path / "app" / "orchestration" / "healing_pipeline.py"
        content = healing_file.read_text(encoding="utf-8")
        
        checks = [
            ("contracts_path = self.project_path / \"contracts.md\"", "Checks contracts.md"),
            ("mock_path = self.project_path / \"frontend\" / \"src\" / \"data\" / \"mock.js\"", "Checks mock.js"),
            ("Discovered entity from contracts.md", "Logs contract discovery"),
            ("Discovered entity from mock.js", "Logs mock discovery"),
        ]
        
        all_passed = True
        for check_str, description in checks:
            if check_str in content:
                print(f"  ✅ {description}")
            else:
                print(f"  ❌ Missing: {description}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Healing pipeline check failed: {e}")
        return False


def test_parser_salvage_function():
    """Test that parser has salvage function."""
    try:
        parser_file = backend_path / "app" / "utils" / "parser.py"
        content = parser_file.read_text(encoding="utf-8")
        
        if "def _salvage_complete_functions(code: str)" in content:
            print("✅ Parser has _salvage_complete_functions()")
        else:
            print("❌ Parser missing _salvage_complete_functions()")
            return False
        
        if "salvaged_content = _salvage_complete_functions(content)" in content:
            print("✅ Parser uses salvage function for truncated code")
            return True
        else:
            print("❌ Parser does NOT use salvage function")
            return False
            
    except Exception as e:
        print(f"❌ Parser check failed: {e}")
        return False


def test_handlers_use_policy():
    """Test that handlers use token policy."""
    try:
        handlers = [
            ("supervisor.py", "Marcus reviews"),
            ("analysis.py", "Analysis step"),
            ("contracts.py", "Contracts step"),
        ]
        
        all_passed = True
        for handler_name, description in handlers:
            if handler_name == "supervisor.py":
                handler_file = backend_path / "app" / "supervision" / handler_name
            else:
                handler_file = backend_path / "app" / "handlers" / handler_name
            
            content = handler_file.read_text(encoding="utf-8")
            
            if "from app.orchestration.token_policy import get_tokens_for_step" in content:
                print(f"  ✅ {description} uses token policy")
            else:
                print(f"  ❌ {description} does NOT use token policy")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Handlers check failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("VERIFICATION: Token Policy Implementation (Options 1, 2, 3#7)")
    print("=" * 70)
    print()
    
    tests = [
        ("Token Policy Module", test_token_policy_exists),
        ("Token Allocations", test_token_allocations),
        ("sub_agents.py Integration", test_sub_agents_uses_policy),
        ("Derek Prompt Updated", test_derek_prompt_updated),
        ("Healing Entity Discovery", test_healing_entity_discovery),
        ("Parser Salvage Function", test_parser_salvage_function),
        ("Handlers Use Policy", test_handlers_use_policy),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        print("-" * 70)
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Implementation is complete and verified.")
        print("\n✅ Ready for production testing with actual workflows.")
        return 0
    else:
        print(f"\n⚠️ {total_count - passed_count} test(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
