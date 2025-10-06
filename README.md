# pytest-mcp

MCP server providing opinionated pytest execution interface for AI agents.

## Overview

pytest-mcp is a Model Context Protocol (MCP) server that enables AI coding assistants to execute pytest with intelligent test selection, structured result interpretation, and context-aware recommendations.

## Status

This project is in active development. MCP server implementation complete with stdio transport, test discovery, and test execution capabilities.

## Installation

Install via uvx for immediate use:

```bash
uvx --from pytest-mcp pytest-mcp
```

Or add to your Python environment:

```bash
pip install pytest-mcp
```

## MCP Integration

pytest-mcp provides a Model Context Protocol server that enables AI coding assistants to execute pytest with intelligent test selection and structured result interpretation.

### Claude Code Configuration

Add pytest-mcp to your Claude Code MCP settings. The configuration file location depends on your platform:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Example configuration:

```json
{
  "mcpServers": {
    "pytest-mcp": {
      "command": "uvx",
      "args": ["--from", "pytest-mcp", "pytest-mcp"]
    }
  }
}
```

**Why uvx?** Ensures you always use the latest version without manual updates. Alternative: use `pytest-mcp` directly if installed in your system Python.

### Available Tools

#### `discover_tests`

Discover pytest test structure without executing tests.

**Parameters:**
- `path` (optional): Directory or file path to discover tests within (default: project root)
- `pattern` (optional): Test file pattern (default: `test_*.py` or `*_test.py`)

**Returns:** Hierarchical test organization with node IDs for subsequent execution.

**Why use this?** Understand test suite structure before execution. Enables intelligent test selection in TDD workflows.

#### `execute_tests`

Execute pytest tests with validated parameters.

**Parameters:**
- `node_ids` (optional): Specific test node IDs to execute (e.g., `["tests/test_user.py::test_login"]`)
- `markers` (optional): Pytest marker expression (e.g., `"not slow and integration"`)
- `keywords` (optional): Keyword expression for test name matching
- `verbosity` (optional): Output verbosity level (-2 to 2)
- `failfast` (optional): Stop execution on first failure
- `maxfail` (optional): Stop after N failures
- `show_capture` (optional): Include captured stdout/stderr
- `timeout` (optional): Execution timeout in seconds

**Returns:** Structured results including pass/fail status, error messages, stack traces, and test summary.

**Exit Code Handling:**
- **Success response** (exit codes 0, 1, 5): Structured test results with failure details
- **Error response** (exit codes 2, 3, 4): pytest configuration or execution errors

**Why this design?** Test failures are normal TDD workflow outcomes. The tool succeeds when pytest executes successfully, regardless of test pass/fail status.

### Connection Testing

Verify the MCP server is working correctly:

1. **Restart Claude Code** after updating configuration
2. **Check MCP connection**: Look for pytest-mcp in Claude's available tools
3. **Test discovery**: Ask Claude to "discover tests in this project"
4. **Test execution**: Ask Claude to "run all tests"

### Troubleshooting

**MCP server not appearing in Claude Code:**
- Verify JSON configuration syntax (no trailing commas)
- Check file path matches your platform
- Restart Claude Code completely (quit and relaunch)

**Tests not discovered:**
- Verify pytest is installed in your project environment
- Check path parameter points to valid test directory
- Ensure pattern matches your test file naming convention

**Test execution failures:**
- Review error response for pytest configuration issues
- Verify node IDs from discovery match execution parameters
- Check timeout parameter if tests run longer than default

## Development

This project uses Nix for reproducible development environments. To get started:

```bash
# Enter development shell
nix develop

# Run tests
pytest

# Run type checking
mypy src

# Run linting
ruff check src tests

# Run security scanning
bandit -r src
```

## License

MIT License - See LICENSE file for details.
