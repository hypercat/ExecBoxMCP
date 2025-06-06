#!/usr/bin/env python3
"""
Simple test to verify the MCP server can be created without errors.
"""

import sys
import traceback

def test_server_creation():
    """Test that we can create the MCP server without errors."""
    try:
        print("Testing MCP server creation...")
        
        # Import and create the server
        from src.execbox.mcp_server import create_mcp_server
        
        print("Creating server...")
        mcp = create_mcp_server("config.json")
        
        print("Listing tools...")
        tools = mcp.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        print("+ Server creation test passed!")
        return True
        
    except Exception as e:
        print(f"- Server creation test failed: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_server_creation()
    sys.exit(0 if success else 1)
