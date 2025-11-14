#!/usr/bin/env python
"""
Test script to verify proper tool registration with Letta using explicit JSON schemas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from letta_client.client import Letta as RESTClient
import json

# Initialize Letta client
client = RESTClient(base_url="http://localhost:8283")

# Test with a simple tool
def test_simple_tool_registration():
    """Test registering a simple tool with explicit schema"""

    # Define the source code as a string (no complex types)
    source_code = '''
def test_hello(name: str, greeting: str = "Hello") -> str:
    """A simple test function that returns a greeting"""
    return f"{greeting}, {name}!"
'''

    # Define the JSON schema explicitly
    json_schema = {
        "name": "test_hello",
        "description": "A simple test function that returns a greeting",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name to greet"
                },
                "greeting": {
                    "type": "string",
                    "description": "The greeting to use",
                    "default": "Hello"
                }
            },
            "required": ["name"]
        }
    }

    try:
        # First, try to delete if it exists
        try:
            existing_tools = client.tools.list()
            for tool in existing_tools:
                if tool.name == "test_hello":
                    client.tools.delete(tool.id)
                    print(f"Deleted existing tool: {tool.id}")
        except Exception as e:
            print(f"Could not check/delete existing tools: {e}")

        # Create the tool with explicit schema
        tool = client.tools.create(
            source_code=source_code,
            json_schema=json_schema
        )

        print(f"✅ Successfully created tool: {tool.id}")
        print(f"   Name: {tool.name}")
        print(f"   Description: {tool.description}")
        return tool

    except Exception as e:
        print(f"❌ Failed to create tool: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_complex_tool_registration():
    """Test registering a more complex tool that would fail with type annotations"""

    # Source code with simplified types (no Dict[str, Any], no Optional)
    source_code = '''
def process_data(data: str, options: str = "") -> dict:
    """Process data with options and return results"""
    import json

    # Parse JSON strings
    data_dict = json.loads(data) if data else {}
    options_dict = json.loads(options) if options else {}

    return {
        "status": "success",
        "data_keys": list(data_dict.keys()),
        "options_keys": list(options_dict.keys()),
        "processed": True
    }
'''

    # Explicit JSON schema
    json_schema = {
        "name": "process_data",
        "description": "Process data with options and return results",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "JSON string containing data to process"
                },
                "options": {
                    "type": "string",
                    "description": "JSON string containing processing options",
                    "default": ""
                }
            },
            "required": ["data"]
        }
    }

    try:
        # Delete if exists
        try:
            existing_tools = client.tools.list()
            for tool in existing_tools:
                if tool.name == "process_data":
                    client.tools.delete(tool.id)
                    print(f"Deleted existing tool: {tool.id}")
        except Exception:
            pass

        # Create tool
        tool = client.tools.create(
            source_code=source_code,
            json_schema=json_schema
        )

        print(f"✅ Successfully created complex tool: {tool.id}")
        print(f"   Name: {tool.name}")
        return tool

    except Exception as e:
        print(f"❌ Failed to create complex tool: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Testing Letta tool registration with explicit JSON schemas...")
    print("=" * 60)

    # Test simple tool
    print("\n1. Testing simple tool registration:")
    simple_tool = test_simple_tool_registration()

    # Test complex tool
    print("\n2. Testing complex tool registration:")
    complex_tool = test_complex_tool_registration()

    # Summary
    print("\n" + "=" * 60)
    if simple_tool and complex_tool:
        print("✅ All tests passed! The approach works.")
        print("\nKey insights:")
        print("- Use client.tools.create() with source_code and json_schema")
        print("- Source code should have simple types (str, dict, list)")
        print("- JSON schema defines the actual parameter types")
        print("- Complex types are handled via JSON serialization")
    else:
        print("❌ Some tests failed. Check the errors above.")