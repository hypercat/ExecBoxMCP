#!/usr/bin/env python3
"""
Standalone runner for ExecBox MCP Server that ensures proper environment setup.
This script can be called from any directory/environment and will use the correct dependencies.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def get_script_dir():
    """Get the directory where this script is located."""
    return Path(__file__).parent.absolute()

def find_uv_executable():
    """Find the uv executable."""
    # Try common locations
    uv_paths = [
        "uv",  # In PATH
        "uv.exe",  # Windows in PATH
        str(Path.home() / ".cargo" / "bin" / "uv"),  # Cargo install
        str(Path.home() / ".cargo" / "bin" / "uv.exe"),  # Cargo install Windows
    ]
    
    for uv_path in uv_paths:
        try:
            result = subprocess.run([uv_path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return uv_path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    raise RuntimeError("Could not find 'uv' executable. Please install uv or ensure it's in your PATH.")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ExecBox MCP Server Runner")
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
    
    # Get the directory where this script is located
    script_dir = get_script_dir()
    
    # Find uv executable
    try:
        uv_executable = find_uv_executable()
        print(f"Using uv executable: {uv_executable}", file=sys.stderr)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build the command to run the server with uv
    cmd = [
        uv_executable,
        "run",
        "--directory", str(script_dir),  # Ensure we run from the correct directory
        "python", "src/main.py",
        "--config", args.config,
        "--log-level", args.log_level
    ]
    
    print(f"Running command: {' '.join(cmd)}", file=sys.stderr)
    print(f"Working directory: {script_dir}", file=sys.stderr)
    
    # Change to the script directory to ensure relative paths work
    original_cwd = os.getcwd()
    os.chdir(script_dir)
    
    try:
        # Run the server with proper stdio handling
        # Use subprocess.Popen to allow stdio passthrough
        print(f"Starting subprocess with command: {cmd}", file=sys.stderr)
        process = subprocess.Popen(cmd, cwd=script_dir)
        print(f"Subprocess started with PID: {process.pid}", file=sys.stderr)
        result = process.wait()
        print(f"Subprocess finished with return code: {result}", file=sys.stderr)
        sys.exit(result)
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Restore original working directory
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()
