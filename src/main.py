import argparse
import logging
import sys
import traceback
import os

def main():
    # Check if we're running in stdio mode (which is what MCP clients expect)
    is_stdio_mode = hasattr(sys.stdin, 'isatty') and not sys.stdin.isatty()
    
    # Function to print debug info (to stderr in stdio mode, stdout otherwise)
    def debug_print(*args, **kwargs):
        if is_stdio_mode:
            print(*args, file=sys.stderr, **kwargs)
        else:
            print(*args, **kwargs)
    
    # Print startup info immediately for debugging
    debug_print("ExecBox MCP Server starting...")
    debug_print(f"Python executable: {sys.executable}")
    debug_print(f"Working directory: {os.getcwd()}")
    debug_print(f"Python path: {sys.path}")
    debug_print(f"Running in {'stdio' if is_stdio_mode else 'interactive'} mode")
    
    # Test imports early
    try:
        debug_print("Testing imports...")
        import asyncio
        debug_print("+ asyncio imported")
        
        import json
        debug_print("+ json imported")
        
        from fastmcp import FastMCP
        debug_print("+ fastmcp imported")
        
        debug_print("+ All basic imports successful")
        
    except Exception as e:
        debug_print(f"FATAL: Import error during startup: {str(e)}")
        debug_print(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)
    
    try:
        # Import our module after basic imports are verified
        from execbox.mcp_server import create_mcp_server
        debug_print("+ execbox.mcp_server imported")
        
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
        debug_print(f"Parsed arguments: config={args.config}, log_level={args.log_level}")
        
        # Set log level for the execbox logger
        logger = logging.getLogger("execbox")
        logger.setLevel(getattr(logging, args.log_level))
        
        debug_print(f"Logger configured with level: {args.log_level}")
        
        logger.info(f"Starting ExecBox MCP Server with config: {args.config}")
        debug_print(f"Creating MCP server with config: {args.config}")
        
        mcp = create_mcp_server(args.config, is_stdio_mode)
        debug_print("MCP server created successfully")
        
        logger.info("MCP Server starting...")
        debug_print("Starting MCP server...")
        debug_print("About to call mcp.run()...")
        
        # Flush output before starting the server
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Add some MCP-specific debugging
        debug_print("MCP server info:")
        debug_print(f"  Server name: {mcp.name}")
        
        # Test tools availability asynchronously
        async def test_tools():
            try:
                tools = await mcp.get_tools()
                if isinstance(tools, dict):
                    tool_names = list(tools.keys())
                    debug_print(f"  Available tools: {len(tools)} - {tool_names}")
                else:
                    debug_print(f"  Tools result type: {type(tools)}")
                    debug_print(f"  Available tools: {tools}")
                return True
            except Exception as e:
                debug_print(f"  Error getting tools: {e}")
                return False
        
        # Run the async test
        tools_ok = asyncio.run(test_tools())
        if not tools_ok:
            debug_print("ERROR: Tools are not accessible!")
            sys.exit(1)
        
        debug_print("Starting MCP server run loop...")
        
        # Add error handling around mcp.run()
        try:
            mcp.run()
        except Exception as run_error:
            debug_print(f"ERROR in mcp.run(): {run_error}")
            debug_print(f"Run error traceback: {traceback.format_exc()}")
            raise
        
    except KeyboardInterrupt:
        debug_print("MCP Server stopped by user (KeyboardInterrupt)")
        try:
            logger = logging.getLogger("execbox")
            logger.info("MCP Server stopped by user")
        except:
            pass
        sys.exit(0)
    except Exception as e:
        debug_print(f"FATAL ERROR: Failed to start MCP Server: {str(e)}")
        debug_print(f"Exception type: {type(e).__name__}")
        debug_print(f"Traceback:\n{traceback.format_exc()}")
        
        try:
            logger = logging.getLogger("execbox")
            logger.error(f"Failed to start MCP Server: {str(e)}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
        except:
            debug_print("Could not write to logger")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
