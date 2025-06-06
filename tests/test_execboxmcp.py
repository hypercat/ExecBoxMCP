#!/usr/bin/env python3
"""
Test suite for PowerShell MCP Server
Tests for security restrictions, command validation, and execution functionality.
"""

import asyncio
import json
import os
import tempfile
import pytest
import pytest_asyncio
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from execbox.mcp_server import PowerShellConfig, PowerShellExecutor, create_mcp_server
from src.main import main


class TestPowerShellConfig:
    """Test the PowerShellConfig class."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
    
    def teardown_method(self):
        """Cleanup after each test."""
        # Use shutil.rmtree for more robust cleanup
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_default_config(self):
        """Test loading default configuration when no config file exists."""
        config = PowerShellConfig(self.config_path)
        
        assert "allowed_commands" in config.config
        assert "allowed_directories" in config.config
        assert "blocked_patterns" in config.config
        assert "max_command_length" in config.config
        assert "timeout_seconds" in config.config
        
        # Check that default commands are present
        assert "Get-ChildItem" in config.config["allowed_commands"]
        assert "Get-Date" in config.config["allowed_commands"]
        
        # Check that config file was created
        assert os.path.exists(self.config_path)
    
    def test_load_custom_config(self):
        """Test loading custom configuration from file."""
        custom_config = {
            "allowed_commands": ["Get-Date", "Get-Host"],
            "allowed_directories": ["C:\\test"],
            "blocked_patterns": ["test_pattern"],
            "max_command_length": 100,
            "timeout_seconds": 15
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)
        
        config = PowerShellConfig(self.config_path)
        
        assert config.config["allowed_commands"] == ["Get-Date", "Get-Host"]
        assert config.config["allowed_directories"] == ["C:\\test"]
        assert config.config["max_command_length"] == 100
        assert config.config["timeout_seconds"] == 15
    
    def test_load_invalid_json_config(self):
        """Test handling of invalid JSON config file."""
        with open(self.config_path, 'w') as f:
            f.write("invalid json content")
        
        # Should fall back to defaults without crashing
        config = PowerShellConfig(self.config_path)
        assert "Get-ChildItem" in config.config["allowed_commands"]
    
    def test_command_allowed_valid(self):
        """Test validation of allowed commands."""
        config = PowerShellConfig(self.config_path)
        
        # Test allowed command
        is_allowed, reason = config.is_command_allowed("Get-Date")
        assert is_allowed is True
        assert reason == "Command is allowed"
        
        # Test allowed command with parameters
        is_allowed, reason = config.is_command_allowed("Get-ChildItem C:\\temp")
        assert is_allowed is True
    
    def test_command_blocked_not_in_whitelist(self):
        """Test blocking of commands not in whitelist."""
        config = PowerShellConfig(self.config_path)
        
        # Use a command that's not blocked by patterns but not in whitelist
        is_allowed, reason = config.is_command_allowed("New-Item myfile.txt")
        assert is_allowed is False
        assert "not in the allowed commands list" in reason
    
    def test_command_blocked_by_pattern(self):
        """Test blocking of commands by regex patterns."""
        config = PowerShellConfig(self.config_path)
        
        # Test semicolon separator
        is_allowed, reason = config.is_command_allowed("Get-Date; Get-Host")
        assert is_allowed is False
        assert "blocked pattern" in reason
        
        # Test pipe separator
        is_allowed, reason = config.is_command_allowed("Get-Item | Select-Object Name")
        assert is_allowed is False
        assert "blocked pattern" in reason
        
        # Test script file
        is_allowed, reason = config.is_command_allowed("Get-Date script.ps1")
        assert is_allowed is False
        assert "blocked pattern" in reason
    
    def test_command_blocked_remove_item_pattern(self):
        """Test that Remove-Item is blocked by pattern matching."""
        config = PowerShellConfig(self.config_path)
        
        is_allowed, reason = config.is_command_allowed("Remove-Item myfile.txt")
        assert is_allowed is False
        assert "blocked pattern" in reason
    
    def test_command_blocked_too_long(self):
        """Test blocking of commands that are too long."""
        config = PowerShellConfig(self.config_path)
        
        long_command = "Get-Date " + "x" * 300
        is_allowed, reason = config.is_command_allowed(long_command)
        assert is_allowed is False
        assert "exceeds maximum length" in reason
    
    def test_command_case_insensitive(self):
        """Test that command validation is case insensitive."""
        config = PowerShellConfig(self.config_path)
        
        # Test uppercase
        is_allowed, reason = config.is_command_allowed("GET-DATE")
        assert is_allowed is True
        
        # Test mixed case
        is_allowed, reason = config.is_command_allowed("Get-date")
        assert is_allowed is True
    
    def test_directory_allowed(self):
        """Test directory permission checking."""
        config = PowerShellConfig(self.config_path)
        
        # Test allowed directory
        assert config.is_directory_allowed("C:\\temp") is True
        assert config.is_directory_allowed("C:\\temp\\subfolder") is True
        
        # Test disallowed directory
        assert config.is_directory_allowed("C:\\Windows") is False
        assert config.is_directory_allowed("D:\\restricted") is False


class TestPowerShellExecutor:
    """Test the PowerShellExecutor class."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config = PowerShellConfig(self.config_path)
        self.executor = PowerShellExecutor(self.config)
    
    def teardown_method(self):
        """Cleanup after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_execute_blocked_command(self):
        """Test that blocked commands are rejected without execution."""
        result = await self.executor.execute_command("Remove-Item myfile.txt")
        
        assert result["success"] is False
        assert "Command blocked" in result["error"]
        assert result["stdout"] == ""
        assert result["stderr"] == ""
    
    @pytest.mark.asyncio
    async def test_execute_invalid_directory(self):
        """Test execution with invalid working directory."""
        result = await self.executor.execute_command(
            "Get-Date", 
            working_directory="/nonexistent/path/that/does/not/exist"
        )
        
        assert result["success"] is False
        assert "Directory does not exist" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_disallowed_directory(self):
        """Test execution in disallowed directory."""
        # Create a real directory that's not in allowed list
        test_dir = os.path.join(self.temp_dir, "disallowed")
        os.makedirs(test_dir, exist_ok=True)
        
        try:
            result = await self.executor.execute_command(
                "Get-Date",
                working_directory=test_dir
            )
            
            assert result["success"] is False
            assert "Directory not allowed" in result["error"]
        finally:
            # Ensure cleanup even if test fails
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_execute_successful_command(self, mock_subprocess):
        """Test successful command execution."""
        # Mock successful process
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b"Mock output", b""
        ))
        mock_subprocess.return_value = mock_process
        
        result = await self.executor.execute_command("Get-Date")
        
        assert result["success"] is True
        assert result["return_code"] == 0
        assert result["stdout"] == "Mock output"
        assert result["stderr"] == ""
        assert result["command"] == "Get-Date"
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_execute_command_with_stderr(self, mock_subprocess):
        """Test command execution with stderr output."""
        # Mock process with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(
            b"", b"Mock error message"
        ))
        mock_subprocess.return_value = mock_process
        
        result = await self.executor.execute_command("Get-Date")
        
        assert result["success"] is False
        assert result["return_code"] == 1
        assert result["stdout"] == ""
        assert result["stderr"] == "Mock error message"
    
    @pytest.mark.asyncio
    @patch('asyncio.wait_for')
    @patch('asyncio.create_subprocess_exec')
    async def test_execute_command_timeout(self, mock_subprocess, mock_wait_for):
        """Test command execution timeout."""
        mock_wait_for.side_effect = asyncio.TimeoutError()
        
        result = await self.executor.execute_command("Get-Date")
        
        assert result["success"] is False
        assert "timed out" in result["error"]
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_execute_command_exception(self, mock_subprocess):
        """Test handling of execution exceptions."""
        mock_subprocess.side_effect = Exception("Mock exception")
        
        result = await self.executor.execute_command("Get-Date")
        
        assert result["success"] is False
        assert "Execution error" in result["error"]
        assert "Mock exception" in result["error"]


class TestSecurityPatterns:
    """Test specific security pattern blocking."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config = PowerShellConfig(self.config_path)
    
    def teardown_method(self):
        """Cleanup after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_block_command_chaining(self):
        """Test blocking of various command chaining methods."""
        dangerous_commands = [
            "Get-Date; Get-Host",
            "Get-Date & Get-Host", 
            "Get-Date | Select-Object",
            "Get-Date `; Get-Host"
        ]
        
        for cmd in dangerous_commands:
            is_allowed, reason = self.config.is_command_allowed(cmd)
            assert is_allowed is False, f"Command should be blocked: {cmd}"
            assert "blocked pattern" in reason
    
    def test_block_script_execution(self):
        """Test blocking of script file execution."""
        script_commands = [
            "Get-Date script.ps1",
            "Get-Date file.bat",
            "Get-Date program.exe",
            "Get-Date command.cmd"
        ]
        
        for cmd in script_commands:
            is_allowed, reason = self.config.is_command_allowed(cmd)
            assert is_allowed is False, f"Script command should be blocked: {cmd}"
    
    def test_block_dangerous_cmdlets(self):
        """Test blocking of dangerous PowerShell cmdlets."""
        dangerous_cmdlets = [
            "Invoke-Expression Get-Date",
            "Start-Process notepad.exe"
        ]
        
        for cmd in dangerous_cmdlets:
            is_allowed, reason = self.config.is_command_allowed(cmd)
            assert is_allowed is False, f"Dangerous cmdlet should be blocked: {cmd}"
    
    def test_block_file_operations(self):
        """Test blocking of destructive file operations."""
        file_ops = [
            "Remove-Item myfile.txt",
            "Get-Date rmdir myfolder"  # rm pattern in parameter
        ]
        
        for cmd in file_ops:
            is_allowed, reason = self.config.is_command_allowed(cmd)
            assert is_allowed is False, f"File operation should be blocked: {cmd}"
    
    def test_block_network_operations(self):
        """Test blocking of network-related operations."""
        # Test patterns that should actually be blocked by the regex
        network_ops = [
            "Invoke-WebRequest http://example.com",
            "Invoke-RestMethod http://example.com"
        ]
        
        for cmd in network_ops:
            is_allowed, reason = self.config.is_command_allowed(cmd)
            assert is_allowed is False, f"Network operation should be blocked: {cmd}"
    
    def test_wget_curl_in_parameters_not_blocked(self):
        """Test that wget/curl as parameters (not commands) are allowed if the primary command is allowed."""
        # These should be allowed because the primary command (Get-Date) is allowed
        # and wget/curl are just parameters, not actual network operations
        parameter_commands = [
            "Get-Date wget",
            "Get-Date curl"
        ]
        
        for cmd in parameter_commands:
            is_allowed, reason = self.config.is_command_allowed(cmd)
            # These should be allowed since Get-Date is allowed and wget/curl are just parameters
            assert is_allowed is True, f"Command with parameter should be allowed: {cmd}"


class TestMCPTools:
    """Test the MCP tool functions (integration tests)."""
    
    def setup_method(self):
        """Setup for MCP tool tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        
        # Set up the global config and executor for the MCP tools
        # We need to patch the global instances in the module
        self.config_patch = patch('execbox.mcp_server.config')
        self.executor_patch = patch('execbox.mcp_server.executor')
        
        self.mock_config = self.config_patch.start()
        self.mock_executor = self.executor_patch.start()
        
        # Create actual config for testing
        self.test_config = PowerShellConfig(self.config_path)
        self.mock_config.config = self.test_config.config
        self.mock_config.is_command_allowed = self.test_config.is_command_allowed
    
    def teardown_method(self):
        """Cleanup after each test."""
        self.config_patch.stop()
        self.executor_patch.stop()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_validate_command_tool(self):
        """Test the validate_command MCP tool."""
        # Import the implementation function
        from execbox.mcp_server import validate_command_impl
        
        # Test valid command
        result = await validate_command_impl("Get-Date")
        assert result["is_allowed"] is True
        assert result["command"] == "Get-Date"
        
        # Test invalid command
        result = await validate_command_impl("New-Item file.txt")
        assert result["is_allowed"] is False
        assert "not in the allowed commands list" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_list_allowed_commands_tool(self):
        """Test the list_allowed_commands MCP tool."""
        from execbox.mcp_server import list_allowed_commands_impl
        
        result = await list_allowed_commands_impl()
        assert isinstance(result, list)
        assert "Get-Date" in result
        assert "Get-ChildItem" in result
    
    @pytest.mark.asyncio
    async def test_list_allowed_directories_tool(self):
        """Test the list_allowed_directories MCP tool."""
        from execbox.mcp_server import list_allowed_directories_impl
        
        result = await list_allowed_directories_impl()
        assert isinstance(result, list)
        assert any("temp" in dir_path.lower() for dir_path in result)
    
    @pytest.mark.asyncio
    async def test_get_security_config_tool(self):
        """Test the get_security_config MCP tool."""
        from execbox.mcp_server import get_security_config_impl
        
        result = await get_security_config_impl()
        assert "allowed_commands_count" in result
        assert "allowed_directories_count" in result
        assert "blocked_patterns_count" in result
        assert "max_command_length" in result
        assert "timeout_seconds" in result
        assert isinstance(result["allowed_commands_count"], int)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Setup for edge case tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config = PowerShellConfig(self.config_path)
    
    def teardown_method(self):
        """Cleanup after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_empty_command(self):
        """Test handling of empty commands."""
        is_allowed, reason = self.config.is_command_allowed("")
        assert is_allowed is False
        assert "not in the allowed commands list" in reason
    
    def test_whitespace_only_command(self):
        """Test handling of whitespace-only commands."""
        is_allowed, reason = self.config.is_command_allowed("   ")
        assert is_allowed is False
    
    def test_command_with_extra_spaces(self):
        """Test handling of commands with extra whitespace."""
        is_allowed, reason = self.config.is_command_allowed("  Get-Date  ")
        assert is_allowed is True
    
    def test_unicode_in_command(self):
        """Test handling of Unicode characters in commands."""
        is_allowed, reason = self.config.is_command_allowed("Get-Date 文件名")
        assert is_allowed is True  # Should be allowed if primary command is valid
    
    def test_very_long_allowed_command(self):
        """Test that even allowed commands are blocked if too long."""
        # Create a command that starts with allowed cmdlet but is too long
        long_param = "x" * 300
        long_command = f"Get-Date {long_param}"
        
        is_allowed, reason = self.config.is_command_allowed(long_command)
        assert is_allowed is False
        assert "exceeds maximum length" in reason


class TestArgumentParsing:
    """Test the argument parsing functionality in main.py."""
    
    @patch('src.main.create_mcp_server')
    @patch('sys.argv', ['main.py'])
    def test_default_config_path(self, mock_create_mcp_server):
        """Test that default config.json is used when no arguments provided."""
        mock_mcp = Mock()
        mock_create_mcp_server.return_value = mock_mcp
        
        try:
            main()
        except SystemExit:
            pass  # main() calls mcp.run() which might exit
        
        mock_create_mcp_server.assert_called_once_with("config.json")
    
    @patch('src.main.create_mcp_server')
    @patch('sys.argv', ['main.py', '--config', 'custom_config.json'])
    def test_custom_config_path_long_arg(self, mock_create_mcp_server):
        """Test custom config path with --config argument."""
        mock_mcp = Mock()
        mock_create_mcp_server.return_value = mock_mcp
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_create_mcp_server.assert_called_once_with("custom_config.json")
    
    @patch('src.main.create_mcp_server')
    @patch('sys.argv', ['main.py', '-c', 'another_config.json'])
    def test_custom_config_path_short_arg(self, mock_create_mcp_server):
        """Test custom config path with -c argument."""
        mock_mcp = Mock()
        mock_create_mcp_server.return_value = mock_mcp
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_create_mcp_server.assert_called_once_with("another_config.json")
    
    @patch('sys.argv', ['main.py', '--help'])
    def test_help_argument(self):
        """Test that help argument works."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        # argparse exits with code 0 for help
        assert exc_info.value.code == 0


class TestMCPServerCreation:
    """Test the create_mcp_server function."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
    
    def teardown_method(self):
        """Cleanup after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_mcp_server_default_config(self):
        """Test creating MCP server with default config path."""
        mcp_server = create_mcp_server(self.config_path)
        
        # Verify that the server was created
        assert mcp_server is not None
        
        # Verify that global config and executor were initialized
        from execbox.mcp_server import config, executor
        assert config is not None
        assert executor is not None
        assert isinstance(config, PowerShellConfig)
        assert isinstance(executor, PowerShellExecutor)
    
    def test_create_mcp_server_custom_config(self):
        """Test creating MCP server with custom config."""
        # Create a custom config file
        custom_config = {
            "allowed_commands": ["Get-Date", "Get-Host"],
            "allowed_directories": ["C:\\test"],
            "blocked_patterns": ["test_pattern"],
            "max_command_length": 100,
            "timeout_seconds": 15
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)
        
        mcp_server = create_mcp_server(self.config_path)
        
        # Verify that the custom config was loaded
        from execbox.mcp_server import config
        assert config.config["allowed_commands"] == ["Get-Date", "Get-Host"]
        assert config.config["max_command_length"] == 100
        assert config.config["timeout_seconds"] == 15
    
    def test_create_mcp_server_nonexistent_config(self):
        """Test creating MCP server with nonexistent config file."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        mcp_server = create_mcp_server(nonexistent_path)
        
        # Should create server with default config and create the config file
        assert mcp_server is not None
        assert os.path.exists(nonexistent_path)
        
        # Verify default config was used
        from execbox.mcp_server import config
        assert "Get-ChildItem" in config.config["allowed_commands"]
        assert config.config["max_command_length"] == 200
    
    def test_create_mcp_server_multiple_calls(self):
        """Test that multiple calls to create_mcp_server work correctly."""
        # First call
        mcp_server1 = create_mcp_server(self.config_path)
        from execbox.mcp_server import config as config1, executor as executor1
        
        # Create a different config file
        config_path2 = os.path.join(self.temp_dir, "test_config2.json")
        custom_config = {
            "allowed_commands": ["Get-Date"],
            "max_command_length": 50
        }
        with open(config_path2, 'w') as f:
            json.dump(custom_config, f)
        
        # Second call with different config
        mcp_server2 = create_mcp_server(config_path2)
        from execbox.mcp_server import config as config2, executor as executor2
        
        # Verify that the global variables were updated
        assert config2.config["max_command_length"] == 50
        assert len(config2.config["allowed_commands"]) == 1


class TestConfigPathIntegration:
    """Test integration between argument parsing and config loading."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "integration_config.json")
        
        # Create a test config file
        test_config = {
            "allowed_commands": ["Get-Date", "Get-Location"],
            "allowed_directories": ["C:\\integration_test"],
            "max_command_length": 150,
            "timeout_seconds": 20
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(test_config, f)
    
    def teardown_method(self):
        """Cleanup after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.main.create_mcp_server')
    @patch('sys.argv')
    def test_end_to_end_config_loading(self, mock_argv, mock_create_mcp_server):
        """Test end-to-end config loading from command line to server creation."""
        mock_argv.__getitem__.side_effect = lambda x: ['main.py', '--config', self.config_path][x]
        mock_argv.__len__.return_value = 3
        
        mock_mcp = Mock()
        mock_create_mcp_server.return_value = mock_mcp
        
        try:
            main()
        except SystemExit:
            pass
        
        # Verify that create_mcp_server was called with the correct config path
        mock_create_mcp_server.assert_called_once_with(self.config_path)
    
    def test_actual_config_loading_integration(self):
        """Test actual config loading without mocking."""
        # This tests the real integration without mocks
        mcp_server = create_mcp_server(self.config_path)
        
        from execbox.mcp_server import config
        
        # Verify the custom config was loaded correctly
        assert config.config["allowed_commands"] == ["Get-Date", "Get-Location"]
        assert config.config["allowed_directories"] == ["C:\\integration_test"]
        assert config.config["max_command_length"] == 150
        assert config.config["timeout_seconds"] == 20
        
        # Test that the config actually works
        is_allowed, reason = config.is_command_allowed("Get-Date")
        assert is_allowed is True
        
        is_allowed, reason = config.is_command_allowed("Get-ChildItem")
        assert is_allowed is False  # Not in our custom allowed list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
