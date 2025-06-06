import argparse
from execbox.mcp_server import create_mcp_server

def main():
    parser = argparse.ArgumentParser(description="ExecBox MCP Server - Secure PowerShell command execution")
    parser.add_argument(
        "--config", 
        "-c", 
        default="config.json",
        help="Path to the configuration JSON file (default: config.json)"
    )
    
    args = parser.parse_args()
    
    mcp = create_mcp_server(args.config)
    mcp.run()

if __name__ == "__main__":
    main()
