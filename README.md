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

1. Clone this repository
2. Install dependencies:
   ```bash
   uv sync
   ```

### Installation with Development Dependencies

```bash
# Install with development dependencies for testing
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

## Configuration

Edit `config.json` to customize security settings:

```json
{
  "allowed_commands": [
    "Get-ChildItem", "Get-Date", "git", "cargo", "npm", "python"
  ],
  "allowed_directories": [
    "C:\\Users\\Public",
    "C:\\Projects\\*",
    "D:\\Development\\*"
  ],
  "blocked_patterns": [
    "[;&|`]", "Invoke-Expression", "\\.ps1"
  ],
  "max_command_length": 200,
  "timeout_seconds": 30
}
```

### Configuration Options

- **allowed_commands**: List of permitted commands (supports both PowerShell cmdlets and external tools)
- **allowed_directories**: Permitted working directories (supports wildcards with `*`)
- **blocked_patterns**: Regex patterns that will block command execution
- **max_command_length**: Maximum length of commands in characters
- **timeout_seconds**: Maximum execution time for commands

## Usage

### Direct Execution

Run the server directly:

```bash
python src/main.py --config config.json
```

Options:
- `--config, -c`: Path to configuration file (default: config.json)
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--enable-file-logging`: Enable logging to file with rotation

### MCP Client Integration

For use with MCP clients like fast-agent, use the direct runner script:

```bash
python run_execboxmcp_direct.py --config config.json
```

The `run_execboxmcp_direct.py` script is specifically designed for MCP client compatibility. It:
- Runs the server directly without uv wrapper complexity
- Properly handles stdio communication required by MCP protocol
- Sets up Python paths correctly for module imports
- Avoids environment isolation issues that can occur with uv-based execution

### Fast-Agent Configuration

Add to your `fastagent.config.yaml`:

```yaml
mcp:
  servers:
    execboxmcp:
      command: "python"
      args: ["path/to/execboxmcp/run_execboxmcp_direct.py", "--config", "path/to/config.json"]
```

## Available MCP Tools

The server provides these MCP tools:

1. **execute_powershell**: Execute a PowerShell command with security restrictions
2. **list_allowed_commands**: Get the list of allowed commands
3. **list_allowed_directories**: Get the list of allowed directories
4. **get_security_config**: Get current security configuration
5. **validate_command**: Validate a command without executing it

## Examples

### Basic Commands
```powershell
Get-Date
Get-ChildItem C:\Users\Public
```

### External Tools (when configured)
```bash
git status
git log --oneline -10
cargo build --release
npm install
python --version
```

### Directory Operations
```powershell
Set-Location C:\Users\Public
Get-ChildItem | Where-Object {$_.Name -like "*.txt"}
```

## Security Considerations

- Commands are executed with PowerShell's restricted execution policy
- All command arguments are validated against security patterns
- Working directories must be explicitly allowed
- Command chaining and piping are blocked by default
- Script file execution (.ps1, .bat, .cmd) is prevented
- Dangerous cmdlets like `Invoke-Expression` are blocked

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
├── run_execboxmcp_direct.py    # Direct runner for MCP clients
├── config.json                 # Default configuration file
├── pyproject.toml              # Project metadata and dependencies
├── uv.lock                     # Locked dependency versions
└── README.md                   # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass with `python -m pytest tests/ -v`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security Considerations

ExecBoxMCP is designed for controlled environments and should be used with caution:

- Review and customize the configuration for your specific use case
- Regularly audit allowed commands and directories
- Monitor command execution logs (enable with `--enable-file-logging`)
- Keep the allowed command list minimal
- Test security configurations thoroughly before deployment

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
