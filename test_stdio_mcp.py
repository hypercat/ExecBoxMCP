#!/usr/bin/env python3
"""
Test MCP server via stdio transport (simulating what fast-agent does).
"""

import asyncio
import json
import subprocess
import sys
import traceback
from pathlib import Path

async def test_stdio_mcp():
    """Test the MCP server via stdio transport."""
    try:
        print("Testing MCP server via stdio transport...")
        
        # Get the path to our main script
        script_dir = Path(__file__).parent
        main_script = script_dir / "src" / "main.py"
        
        print(f"Starting server: python {main_script}")
        
        # Start the server process
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(main_script),
            "--config", "config.json",
            "--log-level", "DEBUG",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=script_dir
        )
        
        print("Server process started, sending initialize message...")
        
        # Send initialize message (what fast-agent would send)
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # Send the message
        message_str = json.dumps(init_message) + "\n"
        print(f"Sending: {message_str.strip()}")
        
        process.stdin.write(message_str.encode())
        await process.stdin.drain()
        
        # Wait for response with timeout
        try:
            stdout_data = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=10.0
            )
            
            if stdout_data:
                response = stdout_data.decode().strip()
                print(f"Received: {response}")
                
                # Try to parse as JSON
                try:
                    response_json = json.loads(response)
                    print(f"Parsed response: {response_json}")
                    print("+ stdio MCP test passed!")
                    return True
                except json.JSONDecodeError as e:
                    print(f"- Response is not valid JSON: {e}")
                    print(f"Raw response: {repr(response)}")
            else:
                print("- No response received")
                
        except asyncio.TimeoutError:
            print("- Timeout waiting for response")
            
        # Check if process is still running
        if process.returncode is None:
            print("Process is still running, terminating...")
            process.terminate()
            await process.wait()
        else:
            print(f"Process exited with code: {process.returncode}")
            
        # Get any stderr output
        try:
            stderr_data = await asyncio.wait_for(
                process.stderr.read(),
                timeout=1.0
            )
            if stderr_data:
                stderr_str = stderr_data.decode()
                print(f"Server stderr: {stderr_str}")
        except asyncio.TimeoutError:
            pass
            
        return False
        
    except Exception as e:
        print(f"- stdio MCP test failed: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_stdio_mcp())
    sys.exit(0 if success else 1)
