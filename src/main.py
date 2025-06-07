import argparse
import logging
import logging.handlers
import sys
import traceback
import os

def setup_logging(enable_file_logging: bool = False, log_level: str = "INFO", is_stdio_mode: bool = False):
    """Set up logging with optional file rotation."""
    try:
        if not is_stdio_mode:
            print("Setting up logging system...")
        
        logger = logging.getLogger("execbox")
        
        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        logger.setLevel(getattr(logging, log_level))
        
        # Only create file handler if file logging is enabled
        if enable_file_logging:
            # Create logs directory if it doesn't exist
            os.makedirs("logs", exist_ok=True)
            if not is_stdio_mode:
                print("+ Logs directory created/verified")
            
            # File handler with rotation (1MB max, keep 5 files)
            file_handler = logging.handlers.RotatingFileHandler(
                "logs/execbox.log",
                maxBytes=1024*1024,  # 1MB
                backupCount=5
            )
            file_handler.setLevel(getattr(logging, log_level))
            if not is_stdio_mode:
                print("+ File handler created")
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            if not is_stdio_mode:
                print("+ File logging enabled")
        else:
            if not is_stdio_mode:
                print("+ File logging disabled")
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        if not is_stdio_mode:
            print("+ Console handler created")
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        if not is_stdio_mode:
            print("+ Handlers added to logger")
        
        # Test log to ensure it's working
        logger.info("Logging system initialized successfully")
        if not is_stdio_mode:
            print("+ Test log written successfully")
        
        return logger
    except Exception as e:
        # Fallback to basic logging if setup fails
        if not is_stdio_mode:
            print(f"Warning: Failed to setup logging: {e}")
            print(f"Logging setup traceback: {traceback.format_exc()}")
        basic_logger = logging.getLogger("execbox")
        basic_logger.setLevel(getattr(logging, log_level))
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        basic_logger.addHandler(handler)
        return basic_logger

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
        parser.add_argument(
            "--enable-file-logging",
            action="store_true",
            help="Enable logging to file (disabled by default)"
        )
        
        args = parser.parse_args()
        debug_print(f"Parsed arguments: config={args.config}, log_level={args.log_level}, enable_file_logging={args.enable_file_logging}")
        
        # Set up logging properly here in main
        logger = setup_logging(
            enable_file_logging=args.enable_file_logging,
            log_level=args.log_level,
            is_stdio_mode=is_stdio_mode
        )
        
        debug_print(f"Logger configured with level: {args.log_level}")
        
        # Import our module after logging is set up
        from execbox.mcp_server import create_mcp_server
        debug_print("+ execbox.mcp_server imported")
        
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
