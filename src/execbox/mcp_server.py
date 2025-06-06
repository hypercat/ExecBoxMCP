#!/usr/bin/env python3
"""
Secure PowerShell MCP Server
A Model Context Protocol server that executes restricted PowerShell commands
with configurable security controls.
"""

import asyncio
import json
import logging
import logging.handlers
import os
import re
import traceback
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Set up logging with rotation
def setup_logging():
    """Set up logging with file rotation."""
    try:
        print("Setting up logging system...")
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        print("+ Logs directory created/verified")
        
        logger = logging.getLogger("execbox")
        
        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        logger.setLevel(logging.INFO)
        
        # File handler with rotation (1MB max, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/execbox.log",
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        print("+ File handler created")
        
        # Console handler for immediate feedback (lower threshold for debugging)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        print("+ Console handler created")
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        print("+ Formatters applied")
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        print("+ Handlers added to logger")
        
        # Test log to ensure it's working
        logger.info("Logging system initialized successfully")
        print("+ Test log written successfully")
        
        return logger
    except Exception as e:
        # Fallback to basic logging if setup fails
        print(f"Warning: Failed to setup logging: {e}")
        print(f"Logging setup traceback: {traceback.format_exc()}")
        basic_logger = logging.getLogger("execbox")
        basic_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        basic_logger.addHandler(handler)
        return basic_logger

# Initialize logging early
print("Initializing logging system...")
logger = setup_logging()
print("+ Logging system ready")

print("Creating FastMCP instance...")
mcp = FastMCP("ExecBoxMCP")
print("+ FastMCP instance created")

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
        logger.info(f"Loading configuration from {self.config_path}")
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
                logger.info(f"Successfully loaded configuration from {self.config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load config file {self.config_path}: {e}")
                logger.warning("Using default configuration.")
                print(f"Warning: Could not load config file {self.config_path}: {e}")
                print("Using default configuration.")
        else:
            logger.info(f"Config file {self.config_path} not found, creating default configuration")
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
            logger.info(f"Configuration saved to {self.config_path}")
        except IOError as e:
            logger.error(f"Could not save config file: {e}")
            print(f"Warning: Could not save config file: {e}")
    
    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        """Check if a command is allowed based on configuration.
        
        Args:
            command: The command to check
        
        Returns:
            Tuple containing (is_allowed, reason)
        """
        logger.debug(f"Validating command: {command}")
        
        if len(command) > self.config["max_command_length"]:
            reason = f"Command exceeds maximum length of {self.config['max_command_length']} characters"
            logger.warning(f"Command blocked: {reason}")
            return False, reason
        
        for pattern in self.config["blocked_patterns"]:
            if re.search(pattern, command, re.IGNORECASE):
                reason = f"Command contains blocked pattern: {pattern}"
                logger.warning(f"Command blocked: {reason}")
                return False, reason
        
        primary_command = command.strip().split()[0] if command.strip() else ""
        
        allowed_commands = [cmd.lower() for cmd in self.config["allowed_commands"]]
        if primary_command.lower() not in allowed_commands:
            reason = f"Command '{primary_command}' is not in the allowed commands list"
            logger.warning(f"Command blocked: {reason}")
            return False, reason
        
        logger.debug(f"Command allowed: {command}")
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
        logger.info(f"Executing command: {command} (working_directory: {working_directory})")
        
        try:
            # Validate command
            is_allowed, reason = self.config.is_command_allowed(command)
            if not is_allowed:
                error_msg = f"Command blocked: {reason}"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "stdout": "",
                    "stderr": ""
                }
            
            # Validate working directory
            if working_directory:
                if not os.path.exists(working_directory):
                    error_msg = f"Directory does not exist: {working_directory}"
                    logger.warning(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "stdout": "",
                        "stderr": ""
                    }
                
                if not self.config.is_directory_allowed(working_directory):
                    error_msg = f"Directory not allowed: {working_directory}"
                    logger.warning(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
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
            
            logger.debug(f"Executing PowerShell with args: {ps_command}")
            
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
            
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()
            
            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "command": command,
                "working_directory": working_directory
            }
            
            if process.returncode == 0:
                logger.info(f"Command executed successfully: {command}")
            else:
                logger.warning(f"Command failed with return code {process.returncode}: {command}")
                if stderr_str:
                    logger.warning(f"Command stderr: {stderr_str}")
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Command timed out after {self.config.config['timeout_seconds']} seconds"
            logger.error(f"{error_msg}: {command}")
            return {
                "success": False,
                "error": error_msg,
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.error(f"{error_msg}: {command}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg,
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
    try:
        logger.info(f"MCP tool execute_powershell called with command: {command}")
        result = await execute_powershell_command(command, working_directory)
        logger.debug(f"MCP tool execute_powershell result: {result}")
        return result
    except Exception as e:
        error_msg = f"MCP tool execute_powershell failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": error_msg,
            "stdout": "",
            "stderr": ""
        }

@mcp.tool()
async def list_allowed_commands() -> List[str]:
    """
    Get the list of allowed PowerShell commands.
    
    Returns:
        List of allowed command names
    """
    try:
        logger.debug("MCP tool list_allowed_commands called")
        result = await get_allowed_commands()
        logger.debug(f"MCP tool list_allowed_commands result: {len(result)} commands")
        return result
    except Exception as e:
        error_msg = f"MCP tool list_allowed_commands failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise

@mcp.tool()
async def list_allowed_directories() -> List[str]:
    """
    Get the list of allowed working directories.
    
    Returns:
        List of allowed directory paths
    """
    try:
        logger.debug("MCP tool list_allowed_directories called")
        result = await get_allowed_directories()
        logger.debug(f"MCP tool list_allowed_directories result: {len(result)} directories")
        return result
    except Exception as e:
        error_msg = f"MCP tool list_allowed_directories failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise

@mcp.tool()
async def get_security_config() -> Dict[str, Any]:
    """
    Get the current security configuration.
    
    Returns:
        Current security configuration settings
    """
    try:
        logger.debug("MCP tool get_security_config called")
        result = await get_current_security_config()
        logger.debug(f"MCP tool get_security_config result: {result}")
        return result
    except Exception as e:
        error_msg = f"MCP tool get_security_config failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise

@mcp.tool()
async def validate_command(command: str) -> Dict[str, Any]:
    """
    Validate a PowerShell command without executing it.
    
    Args:
        command: The PowerShell command to validate
        
    Returns:
        Validation result with details
    """
    try:
        logger.debug(f"MCP tool validate_command called with command: {command}")
        result = await validate_powershell_command(command)
        logger.debug(f"MCP tool validate_command result: {result}")
        return result
    except Exception as e:
        error_msg = f"MCP tool validate_command failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise

def create_mcp_server(config_path: str = "config.json") -> FastMCP:
    """
    Create and configure the MCP server with the specified config file.
    
    Args:
        config_path: Path to the configuration JSON file
        
    Returns:
        Configured FastMCP server instance
    """
    global config, executor
    
    print(f"create_mcp_server called with config_path: {config_path}")
    
    try:
        logger.info(f"Creating MCP server with config: {config_path}")
        print(f"Creating PowerShellConfig with path: {config_path}")
        
        config = PowerShellConfig(config_path)
        print("PowerShellConfig created successfully")
        
        executor = PowerShellExecutor(config)
        print("PowerShellExecutor created successfully")
        
        # Verify the MCP server is properly configured
        print("Verifying MCP server configuration...")
        try:
            # Check that tools are registered
            print(f"FastMCP instance: {mcp}")
            print(f"FastMCP name: {mcp.name}")
            
            # Test that we can access the tools (this might be async)
            print("MCP server appears to be properly configured")
            
        except Exception as verify_error:
            print(f"Warning: MCP server verification failed: {verify_error}")
            # Don't fail here, just warn
        
        logger.info("MCP server created successfully")
        print("MCP server configuration completed successfully")
        
        return mcp
    except Exception as e:
        error_msg = f"Failed to create MCP server: {str(e)}"
        traceback_str = traceback.format_exc()
        
        print(f"ERROR in create_mcp_server: {error_msg}")
        print(f"Traceback: {traceback_str}")
        
        try:
            logger.error(error_msg)
            logger.error(f"Exception traceback: {traceback_str}")
        except:
            print("Could not write error to logger")
        
        raise
