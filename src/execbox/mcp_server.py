#!/usr/bin/env python3
"""
Secure PowerShell MCP Server
A Model Context Protocol server that executes restricted PowerShell commands
with configurable security controls.
"""

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

mcp = FastMCP("ExecBoxMCP")

class PowerShellConfig:
    """Configuration manager for PowerShell execution restrictions."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file.
        
        Returns:
            The loaded configuration dictionary
        """
        default_config = {
            "allowed_commands": [
                "Get-ChildItem", "Get-Item", "Get-Content", "Get-Location",
                "Set-Location", "Test-Path", "Get-Process", "Get-Service",
                "Get-Date", "Get-Host", "Write-Output", "Write-Host",
                "Select-Object", "Where-Object", "Sort-Object", "Measure-Object"
            ],
            "allowed_directories": [
                "C:\\Users\\Public",
                "C:\\temp",
                "C:\\Windows\\System32"
            ],
            "blocked_patterns": [
                r"[;&|`]",  # Command separators and pipes
                r"Invoke-Expression",
                r"Invoke-Command",
                r"Invoke-WebRequest",
                r"Invoke-RestMethod",
                r"iex\s",
                r"icm\s",
                r"Start-Process",
                r"sps\s",
                r"Remove-Item",
                r"rm\s",
                r"del\s",
                r"rmdir\s",
                r"\.ps1",  # Script files
                r"\.bat",  # Batch files
                r"\.cmd",  # Command files
                r"\.exe",  # Executables
                r"powershell\.exe",
                r"cmd\.exe"
            ],
            "max_command_length": 200,
            "timeout_seconds": 30
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    default_config.update(loaded_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file {self.config_path}: {e}")
                print("Using default configuration.")
        else:
            # Create default config file
            self._save_config(default_config)
        
        return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to JSON file.
        
        Args:
            config: The configuration dictionary to save
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config file: {e}")
    
    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        """Check if a command is allowed based on configuration.
        
        Args:
            command: The command to check
        
        Returns:
            Tuple containing (is_allowed, reason)
        """
        if len(command) > self.config["max_command_length"]:
            return False, f"Command exceeds maximum length of {self.config['max_command_length']} characters"
        
        for pattern in self.config["blocked_patterns"]:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command contains blocked pattern: {pattern}"
        
        primary_command = command.strip().split()[0] if command.strip() else ""
        
        allowed_commands = [cmd.lower() for cmd in self.config["allowed_commands"]]
        if primary_command.lower() not in allowed_commands:
            return False, f"Command '{primary_command}' is not in the allowed commands list"
        
        return True, "Command is allowed"
    
    def is_directory_allowed(self, directory: str) -> bool:
        """Check if a directory is in the allowed list.
        
        Args:
            directory: The directory to check
        
        Returns:
            True if the directory is allowed, False otherwise
        """
        abs_dir = os.path.abspath(directory)
        for allowed_dir in self.config["allowed_directories"]:
            abs_allowed = os.path.abspath(allowed_dir)
            if abs_dir.startswith(abs_allowed):
                return True
        return False


class PowerShellExecutor:
    """Secure PowerShell command executor."""
    
    def __init__(self, config: PowerShellConfig):
        self.config = config
    
    async def execute_command(self, command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
        """Execute a PowerShell command with security restrictions."""
        
        # Validate command
        is_allowed, reason = self.config.is_command_allowed(command)
        if not is_allowed:
            return {
                "success": False,
                "error": f"Command blocked: {reason}",
                "stdout": "",
                "stderr": ""
            }
        
        # Validate working directory
        if working_directory:
            if not os.path.exists(working_directory):
                return {
                    "success": False,
                    "error": f"Directory does not exist: {working_directory}",
                    "stdout": "",
                    "stderr": ""
                }
            
            if not self.config.is_directory_allowed(working_directory):
                return {
                    "success": False,
                    "error": f"Directory not allowed: {working_directory}",
                    "stdout": "",
                    "stderr": ""
                }
        
        # Prepare PowerShell command
        ps_command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Restricted",  # Prevent script execution
            "-Command", command
        ]
        
        try:
            # Execute command with timeout
            process = await asyncio.create_subprocess_exec(
                *ps_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.config["timeout_seconds"]
            )
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace').strip(),
                "stderr": stderr.decode('utf-8', errors='replace').strip(),
                "command": command,
                "working_directory": working_directory
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command timed out after {self.config.config['timeout_seconds']} seconds",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "stdout": "",
                "stderr": ""
            }

# Global variables will be initialized by create_mcp_server()
config = None
executor = None

# Business logic functions (these are what the MCP tools call and what we test)
async def execute_powershell_command(command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a PowerShell command with security restrictions.
    
    Args:
        command: The PowerShell command to execute
        working_directory: Optional working directory for command execution
        
    Returns:
        Dictionary containing execution results and metadata
    """
    return await executor.execute_command(command, working_directory)

async def get_allowed_commands() -> List[str]:
    """
    Get the list of allowed PowerShell commands.
    
    Returns:
        List of allowed command names
    """
    return config.config["allowed_commands"]

async def get_allowed_directories() -> List[str]:
    """
    Get the list of allowed working directories.
    
    Returns:
        List of allowed directory paths
    """
    return config.config["allowed_directories"]

async def get_current_security_config() -> Dict[str, Any]:
    """
    Get the current security configuration.
    
    Returns:
        Current security configuration settings
    """
    return {
        "allowed_commands_count": len(config.config["allowed_commands"]),
        "allowed_directories_count": len(config.config["allowed_directories"]),
        "blocked_patterns_count": len(config.config["blocked_patterns"]),
        "max_command_length": config.config["max_command_length"],
        "timeout_seconds": config.config["timeout_seconds"]
    }

async def validate_powershell_command(command: str) -> Dict[str, Any]:
    """
    Validate a PowerShell command without executing it.
    
    Args:
        command: The PowerShell command to validate
        
    Returns:
        Validation result with details
    """
    is_allowed, reason = config.is_command_allowed(command)
    return {
        "is_allowed": is_allowed,
        "reason": reason,
        "command": command
    }

# MCP tools (these call the business logic functions above)
@mcp.tool()
async def execute_powershell(command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a PowerShell command with security restrictions.
    
    Args:
        command: The PowerShell command to execute
        working_directory: Optional working directory for command execution
        
    Returns:
        Dictionary containing execution results and metadata
    """
    return await execute_powershell_command(command, working_directory)

@mcp.tool()
async def list_allowed_commands() -> List[str]:
    """
    Get the list of allowed PowerShell commands.
    
    Returns:
        List of allowed command names
    """
    return await get_allowed_commands()

@mcp.tool()
async def list_allowed_directories() -> List[str]:
    """
    Get the list of allowed working directories.
    
    Returns:
        List of allowed directory paths
    """
    return await get_allowed_directories()

@mcp.tool()
async def get_security_config() -> Dict[str, Any]:
    """
    Get the current security configuration.
    
    Returns:
        Current security configuration settings
    """
    return await get_current_security_config()

@mcp.tool()
async def validate_command(command: str) -> Dict[str, Any]:
    """
    Validate a PowerShell command without executing it.
    
    Args:
        command: The PowerShell command to validate
        
    Returns:
        Validation result with details
    """
    return await validate_powershell_command(command)

def create_mcp_server(config_path: str = "config.json") -> FastMCP:
    """
    Create and configure the MCP server with the specified config file.
    
    Args:
        config_path: Path to the configuration JSON file
        
    Returns:
        Configured FastMCP server instance
    """
    global config, executor
    
    config = PowerShellConfig(config_path)
    executor = PowerShellExecutor(config)
    
    return mcp
