import argparse
import logging
import sys
from execbox.mcp_server import create_mcp_server

def main():
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
    
    # Set log level for the execbox logger
    logger = logging.getLogger("execbox")
    logger.setLevel(getattr(logging, args.log_level))
    
    try:
        logger.info(f"Starting ExecBox MCP Server with config: {args.config}")
        mcp = create_mcp_server(args.config)
        logger.info("MCP Server starting...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start MCP Server: {str(e)}")
        print(f"Error: Failed to start MCP Server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
