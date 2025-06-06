#!/usr/bin/env python3
"""
Direct runner for ExecBox MCP Server for fast-agent compatibility.
This script runs the server directly without uv wrapper.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Main entry point."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Add the src directory to Python path
    src_dir = script_dir / "src"
    sys.path.insert(0, str(src_dir))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Import and run the main function directly
    try:
        from main import main as server_main
        server_main()
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
