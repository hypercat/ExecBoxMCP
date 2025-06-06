import argparse
import logging
import sys
import traceback
from execbox.mcp_server import create_mcp_server

def main():
    # Print startup info immediately for debugging
    print("ExecBox MCP Server starting...")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {sys.path[0] if sys.path else 'unknown'}")
    
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
        
        mcp.run()
        
    except KeyboardInterrupt:
        print("MCP Server stopped by user (KeyboardInterrupt)")
        logger = logging.getLogger("execbox")
        logger.info("MCP Server stopped by user")
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
