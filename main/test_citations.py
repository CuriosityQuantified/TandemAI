"""Test that generated documents have proper citations."""
import re
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from module_2_2_simple import run_agent_task

def test_citations_present():
    """Test that documents include inline citations."""
    print("\n" + "=" * 80)
    print("CITATION VALIDATION TEST")
    print("=" * 80)

    result = run_agent_task(
        "Research LangChain v1.0 and save a brief summary to /workspace/test_citations.md with citations",
        thread_id="citation-test"
    )

    # Define workspace path
    workspace_dir = "/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/agent_workspace"
    file_path = os.path.join(workspace_dir, "test_citations.md")

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ FAILED: File not found at {file_path}")
        return False

    # Read the generated file
    with open(file_path, "r") as f:
        content = f.read()

    print(f"\n📄 Generated Document Content:")
    print("─" * 80)
    print(content[:500] + "..." if len(content) > 500 else content)
    print("─" * 80)

    # Check for inline citations [^1]
    inline_citations = re.findall(r'\[\^(\d+)\]', content)
    print(f"\n🔍 Found {len(inline_citations)} inline citation(s): {inline_citations}")

    if len(inline_citations) == 0:
        print("❌ FAILED: No inline citations found")
        return False
    else:
        print("✅ PASSED: Inline citations present")

    # Check for footer references
    has_reference_section = "## References" in content or "[^1]:" in content
    print(f"\n🔍 Checking for reference footer...")

    if not has_reference_section:
        print("❌ FAILED: No reference footer found")
        return False
    else:
        print("✅ PASSED: Reference footer present")

    # Check that references have URLs
    reference_pattern = r'\[\^(\d+)\]:.*https?://'
    references = re.findall(reference_pattern, content)
    print(f"\n🔍 Found {len(references)} reference(s) with URLs: {references}")

    if len(references) == 0:
        print("❌ FAILED: No URLs in references")
        return False
    else:
        print("✅ PASSED: References include URLs")

    print("\n" + "=" * 80)
    print(f"✅ CITATION TEST PASSED")
    print(f"   - {len(inline_citations)} inline citations")
    print(f"   - {len(references)} references with URLs")
    print("=" * 80)

    return True

if __name__ == "__main__":
    try:
        success = test_citations_present()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
