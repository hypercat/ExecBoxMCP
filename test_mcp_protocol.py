#!/usr/bin/env python3
"""
Test MCP protocol communication directly.
"""

import asyncio
import json
import sys
import traceback
from src.execbox.mcp_server import create_mcp_server

async def test_mcp_protocol():
    """Test the MCP protocol directly."""
    try:
        print("Creating MCP server...")
        mcp = create_mcp_server("config.json")
        
        print("Testing MCP protocol methods...")
        
        # Test initialize
        print("Testing initialize...")
        init_result = await mcp.initialize({
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        print(f"Initialize result: {init_result}")
        
        # Test list tools
        print("Testing list_tools...")
        tools_result = await mcp.get_tools()
        print(f"Tools: {[tool.name for tool in tools_result]}")
        
        # Test a simple tool call
        print("Testing tool call...")
        validation_result = await mcp.call_tool("validate_command", {"command": "Get-Date"})
        print(f"Validation result: {validation_result}")
        
        print("+ MCP protocol test passed!")
        return True
        
    except Exception as e:
        print(f"- MCP protocol test failed: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_protocol())
    sys.exit(0 if success else 1)
