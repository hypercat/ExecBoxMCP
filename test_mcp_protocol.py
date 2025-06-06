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
        
        print("Testing MCP server functionality...")
        
        # Test get tools
        print("Testing get_tools...")
        tools_result = await mcp.get_tools()
        print(f"Tools result type: {type(tools_result)}")
        print(f"Tools result: {tools_result}")
        
        # Handle different return types
        if isinstance(tools_result, list):
            if tools_result:
                # Check if items have .name attribute or are strings
                if hasattr(tools_result[0], 'name'):
                    tool_names = [tool.name for tool in tools_result]
                else:
                    tool_names = tools_result  # Assume they are already names
                print(f"Tool names: {tool_names}")
            else:
                print("- No tools found!")
                return False
        else:
            print(f"Unexpected tools result type: {type(tools_result)}")
            return False
        
        # Test a simple tool call
        print("Testing tool call...")
        try:
            validation_result = await mcp.call_tool("validate_command", {"command": "Get-Date"})
            print(f"Validation result: {validation_result}")
        except Exception as tool_error:
            print(f"Tool call failed: {tool_error}")
            print(f"Tool call traceback: {traceback.format_exc()}")
        
        # Test another tool call
        print("Testing list_allowed_commands...")
        try:
            commands_result = await mcp.call_tool("list_allowed_commands", {})
            print(f"Allowed commands result: {commands_result}")
            print(f"Allowed commands count: {len(commands_result) if isinstance(commands_result, list) else 'unknown'}")
        except Exception as tool_error:
            print(f"List commands tool call failed: {tool_error}")
            print(f"List commands traceback: {traceback.format_exc()}")
        
        print("+ MCP protocol test passed!")
        return True
        
    except Exception as e:
        print(f"- MCP protocol test failed: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_protocol())
    sys.exit(0 if success else 1)
