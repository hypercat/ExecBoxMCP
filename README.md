# ExecBoxMCP

A secure Model Context Protocol (MCP) server that provides restricted PowerShell command execution with configurable security controls.

## Overview

ExecBoxMCP is designed to safely execute PowerShell commands in controlled environments by implementing multiple layers of security:

- **Command Whitelisting**: Only pre-approved commands can be executed
- **Pattern Blocking**: Dangerous patterns and command separators are blocked
- **Directory Restrictions**: Commands can only be executed in allowed directories
- **Timeout Protection**: Commands are automatically terminated after a configurable timeout
- **Execution Policy**: PowerShell runs with restricted execution policy to prevent script execution

## Features

- 🔒 **Secure by Default**: Restrictive configuration prevents dangerous operations
- ⚙️ **Configurable**: JSON-based configuration for commands, directories, and security patterns
- 🚀 **Async Execution**: Non-blocking command execution with timeout support
- 🛠️ **MCP Integration**: Full Model Context Protocol support for AI assistant integration
- 📝 **Comprehensive Logging**: Detailed execution results and error reporting
- 🧪 **Well Tested**: Extensive test suite covering security scenarios and edge cases

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. The dependencies are locked in `uv.lock` for reproducible builds.

```bash
# Clone the repository
git clone <repository-url>
cd ExecBoxMCP

# Install uv if you haven't already
pip install uv

# Install the package and dependencies
uv sync

# Or install with development dependencies
uv sync --extra dev
```

**Alternative installation with pip:**
```bash
# If you prefer to use pip instead of uv
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

1. **Run with default configuration:**
   ```bash
   python src/main.py
   ```

2. **Run with custom configuration:**
   ```bash
   python src/main.py --config my-config.json
   ```

3. **Get help:**
   ```bash
   python src/main.py --help
   ```

## Configuration

ExecBoxMCP uses a JSON configuration file to define security policies. If no config file exists, a default one will be created.

### Default Configuration

```json
{
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
    "[;&|`]",
    "Invoke-Expression",
    "Invoke-Command",
    "Invoke-WebRequest",
    "Invoke-RestMethod",
    "iex\\s",
    "icm\\s",
    "Start-Process",
    "sps\\s",
    "Remove-Item",
    "rm\\s",
    "del\\s",
    "rmdir\\s",
    "\\.ps1",
    "\\.bat",
    "\\.cmd",
    "\\.exe",
    "powershell\\.exe",
    "cmd\\.exe"
  ],
  "max_command_length": 200,
  "timeout_seconds": 30
}
```

### Configuration Options

- **`allowed_commands`**: List of PowerShell cmdlets that are permitted
- **`allowed_directories`**: List of directories where commands can be executed
- **`blocked_patterns`**: Regular expressions for dangerous patterns to block
- **`max_command_length`**: Maximum length of commands in characters
- **`timeout_seconds`**: Maximum execution time before commands are terminated

## MCP Tools

ExecBoxMCP provides the following MCP tools:

### `execute_powershell`
Execute a PowerShell command with security restrictions.

**Parameters:**
- `command` (string): The PowerShell command to execute
- `working_directory` (string, optional): Working directory for execution

**Returns:**
- `success` (boolean): Whether the command executed successfully
- `return_code` (integer): PowerShell exit code
- `stdout` (string): Standard output from the command
- `stderr` (string): Standard error from the command
- `command` (string): The executed command
- `working_directory` (string): The working directory used

### `validate_command`
Validate a PowerShell command without executing it.

**Parameters:**
- `command` (string): The PowerShell command to validate

**Returns:**
- `is_allowed` (boolean): Whether the command would be allowed
- `reason` (string): Explanation of the validation result
- `command` (string): The validated command

### `list_allowed_commands`
Get the list of allowed PowerShell commands.

**Returns:**
- Array of allowed command names

### `list_allowed_directories`
Get the list of allowed working directories.

**Returns:**
- Array of allowed directory paths

### `get_security_config`
Get the current security configuration summary.

**Returns:**
- `allowed_commands_count` (integer): Number of allowed commands
- `allowed_directories_count` (integer): Number of allowed directories
- `blocked_patterns_count` (integer): Number of blocked patterns
- `max_command_length` (integer): Maximum command length
- `timeout_seconds` (integer): Command timeout in seconds

## Security Features

### Command Validation
- Only whitelisted PowerShell cmdlets are allowed
- Commands are checked against blocked patterns using regular expressions
- Command length is limited to prevent abuse
- Case-insensitive validation

### Directory Restrictions
- Commands can only be executed in pre-approved directories
- Path traversal attempts are blocked
- Absolute path resolution prevents bypass attempts

### Execution Safety
- PowerShell runs with `-ExecutionPolicy Restricted` to prevent script execution
- Commands run with `-NoProfile` and `-NonInteractive` flags
- Automatic timeout prevents long-running or hanging commands
- Subprocess isolation limits system access

### Pattern Blocking
The default configuration blocks:
- Command chaining (`;&|` characters)
- Script execution (`Invoke-Expression`, `.ps1` files)
- Network operations (`Invoke-WebRequest`, `Invoke-RestMethod`)
- File deletion operations (`Remove-Item`, `del`, `rm`)
- Process execution (`Start-Process`)
- Executable files (`.exe`, `.bat`, `.cmd`)

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test classes
python -m pytest tests/test_execboxmcp.py::TestPowerShellConfig -v
python -m pytest tests/test_execboxmcp.py::TestMCPTools -v
```

### Project Structure

```
ExecBoxMCP/
├── src/
│   ├── main.py                 # Entry point and argument parsing
│   └── execbox/
│       ├── __init__.py         # Package initialization
│       └── mcp_server.py       # Core MCP server and security logic
├── tests/
│   └── test_execboxmcp.py      # Comprehensive test suite
├── config.json                 # Default configuration file
├── pyproject.toml              # Project metadata and dependencies
├── uv.lock                     # Locked dependency versions
└── README.md                   # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security Considerations

ExecBoxMCP is designed for controlled environments and should be used with caution:

- Review and customize the configuration for your specific use case
- Regularly audit allowed commands and directories
- Monitor command execution logs
- Keep the allowed command list minimal
- Test security configurations thoroughly before deployment

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
