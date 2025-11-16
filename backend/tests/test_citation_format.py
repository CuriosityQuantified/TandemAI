"""
Test script to verify enhanced citation format and LangSmith tracing.
"""
import os
import requests
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv("/Users/nicholaspate/Documents/01_Active/Corp_Strat/open-source-CC/docs/learning-plan/lessons/.env")

print("=" * 80)
print("🧪 Testing Enhanced Citation Format + LangSmith Tracing")
print("=" * 80)
print()

# Verify environment
print("📋 Environment Check:")
print(f"   LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"   LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
print(f"   LANGCHAIN_API_KEY: {'✓ Set' if os.getenv('LANGCHAIN_API_KEY') else '✗ Not Set'}")
print()

# Test query that should trigger researcher with citations
test_query = """Research the ACE (Autonomous Context Extension) framework for AI agents. 
Find 2-3 key facts about how it works, with exact quotes and citations.
Be comprehensive with inline citations using the format: "exact quote" [Source, URL, Date] [1]"""

print("🔍 Test Query:")
print(f"   {test_query[:100]}...")
print()

# Submit to backend
try:
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "message": test_query,
            "thread_id": "test-citations-001"
        },
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Query submitted successfully!")
        print()
        print("📊 Response Preview:")
        print(result.get("response", "No response")[:500])
        print()
        print("🎯 Check LangSmith Dashboard:")
        print("   URL: https://smith.langchain.com")
        print("   Project: module-2-2-research-agent")
        print("   Look for trace with thread_id: test-citations-001")
        print()
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ Backend not running on port 8000")
    print("   Please start backend with: python main.py")
except Exception as e:
    print(f"❌ Exception: {e}")

print("=" * 80)
