import argparse
import logging
import sys
import traceback
import os

def main():
    # Print startup info immediately for debugging
    print("ExecBox MCP Server starting...")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    
    # Test imports early
    try:
        print("Testing imports...")
        import asyncio
        print("+ asyncio imported")
        
        import json
        print("+ json imported")
        
        from fastmcp import FastMCP
        print("+ fastmcp imported")
        
        print("+ All basic imports successful")
        
    except Exception as e:
        print(f"FATAL: Import error during startup: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)
    
    try:
        # Import our module after basic imports are verified
        from execbox.mcp_server import create_mcp_server
        print("+ execbox.mcp_server imported")
        
        parser = argparse.ArgumentParser(description="ExecBox MCP Server - Secure PowerShell command execution")
        parser.add_argument(
            "--config", 
            "-c", 
            default="config.json",
            help="Path to the configuration JSON file (default: config.json)"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Set the logging level (default: INFO)"
        )
        
        args = parser.parse_args()
        print(f"Parsed arguments: config={args.config}, log_level={args.log_level}")
        
        # Set log level for the execbox logger
        logger = logging.getLogger("execbox")
        logger.setLevel(getattr(logging, args.log_level))
        
        print(f"Logger configured with level: {args.log_level}")
        
        logger.info(f"Starting ExecBox MCP Server with config: {args.config}")
        print(f"Creating MCP server with config: {args.config}")
        
        mcp = create_mcp_server(args.config)
        print("MCP server created successfully")
        
        logger.info("MCP Server starting...")
        print("Starting MCP server...")
        print("About to call mcp.run()...")
        
        # Flush output before starting the server
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Add some MCP-specific debugging
        print("MCP server info:")
        print(f"  Server name: {mcp.name}")
        
        # Test tools availability asynchronously
        async def test_tools():
            try:
                tools = await mcp.get_tools()
                print(f"  Available tools: {len(tools)} - {[tool.name for tool in tools]}")
                return True
            except Exception as e:
                print(f"  Error getting tools: {e}")
                return False
        
        # Run the async test
        tools_ok = asyncio.run(test_tools())
        if not tools_ok:
            print("ERROR: Tools are not accessible!")
            sys.exit(1)
        
        # Check if we're running in stdio mode (which is what MCP clients expect)
        if hasattr(sys.stdin, 'isatty') and not sys.stdin.isatty():
            print("Running in stdio mode (non-interactive)")
        else:
            print("Running in interactive mode")
        
        print("Starting MCP server run loop...")
        
        # Add error handling around mcp.run()
        try:
            mcp.run()
        except Exception as run_error:
            print(f"ERROR in mcp.run(): {run_error}")
            print(f"Run error traceback: {traceback.format_exc()}")
            raise
        
    except KeyboardInterrupt:
        print("MCP Server stopped by user (KeyboardInterrupt)")
        try:
            logger = logging.getLogger("execbox")
            logger.info("MCP Server stopped by user")
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR: Failed to start MCP Server: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Traceback:\n{traceback.format_exc()}")
        
        try:
            logger = logging.getLogger("execbox")
            logger.error(f"Failed to start MCP Server: {str(e)}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
        except:
            print("Could not write to logger")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
