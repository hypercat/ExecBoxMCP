#!/usr/bin/env python3
"""
Test script that mimics how fast-agent would connect to our MCP server.
This can be used to debug connection issues.
"""

import asyncio
import json
import subprocess
import sys
import traceback
from pathlib import Path

async def test_fast_agent_connection():
    """Test connection like fast-agent would."""
    try:
        print("Testing fast-agent style connection...")
        
        # Get the path to our runner script
        script_dir = Path(__file__).parent
        runner_script = script_dir / "run_execboxmcp.py"
        
        print(f"Starting server via runner: python {runner_script}")
        
        # Start the server process using our runner
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(runner_script),
            "--config", "config.json",
            "--log-level", "INFO",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=script_dir
        )
        
        print("Server process started via runner...")
        
        # Give the server a moment to start up
        await asyncio.sleep(2)
        
        # Check if process is still running
        if process.returncode is not None:
            print(f"Server process exited early with code: {process.returncode}")
            stderr_data = await process.stderr.read()
            if stderr_data:
                stderr_str = stderr_data.decode()
                print(f"Server stderr: {stderr_str}")
            return False
        
        # Send initialize message
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "experimental": {},
                    "sampling": {},
                    "roots": None
                },
                "clientInfo": {
                    "name": "fast-agent-mcp",
                    "version": "0.2.28"
                }
            }
        }
        
        # Send the message
        message_str = json.dumps(init_message) + "\n"
        print(f"Sending initialize: {message_str.strip()}")
        
        process.stdin.write(message_str.encode())
        await process.stdin.drain()
        
        # Wait for response
        try:
            stdout_data = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=15.0
            )
            
            if stdout_data:
                response = stdout_data.decode().strip()
                print(f"Received: {response}")
                
                try:
                    response_json = json.loads(response)
                    print(f"Initialize successful: {response_json}")
                    
                    # Send tools/list request
                    tools_message = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {}
                    }
                    
                    tools_str = json.dumps(tools_message) + "\n"
                    print(f"Sending tools/list: {tools_str.strip()}")
                    
                    process.stdin.write(tools_str.encode())
                    await process.stdin.drain()
                    
                    # Wait for tools response
                    tools_data = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=10.0
                    )
                    
                    if tools_data:
                        tools_response = tools_data.decode().strip()
                        print(f"Tools response: {tools_response}")
                        
                        try:
                            tools_json = json.loads(tools_response)
                            print(f"Tools available: {len(tools_json.get('result', {}).get('tools', []))}")
                            print("+ Fast-agent style connection test passed!")
                            return True
                        except json.JSONDecodeError as e:
                            print(f"- Tools response not valid JSON: {e}")
                    else:
                        print("- No tools response received")
                    
                except json.JSONDecodeError as e:
                    print(f"- Initialize response not valid JSON: {e}")
                    print(f"Raw response: {repr(response)}")
            else:
                print("- No initialize response received")
                
        except asyncio.TimeoutError:
            print("- Timeout waiting for initialize response")
            
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
        print(f"- Fast-agent connection test failed: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fast_agent_connection())
    sys.exit(0 if success else 1)
