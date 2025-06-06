#!/bin/bash
# ExecBox MCP Server Runner for Unix-like systems
# This script ensures the server runs with the correct environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the Python runner script with all arguments passed through
python3 run_execboxmcp.py "$@"

# Exit with the same code as the Python script
exit $?
