# ADR-012: Console Script Entry Point Configuration

**Status**: accepted

**Date**: October 3, 2025 (Friday)

**Project**: pytest-mcp

## Context

ADR-009, ADR-010, and ADR-011 established the complete MCP server architecture:
- ADR-009: Use MCP SDK with async adapters
- ADR-010: Decorator-based tool routing (`@server.call_tool()`)
- ADR-011: Server lifecycle via `stdio_server()` async context manager with async `main()` function

Story 11 requires users to be able to invoke the pytest-mcp server from the command line and configure it in Claude Code's MCP settings. Currently:
- pyproject.toml has `mcp>=1.16.0` in dependencies
- No `[project.scripts]` entry point defined
- Users cannot invoke `pytest-mcp` command
- Cannot configure in Claude Code's `claude_desktop_config.json`

We must decide how to configure the console script entry point so users can:
1. Run `pytest-mcp` from the command line after installation
2. Configure the server in MCP client settings (Claude Code, etc.)
3. Bridge from synchronous console script invocation to our async `main()` function

Key considerations:

1. **Python Package Entry Points**: `[project.scripts]` in pyproject.toml defines console commands installed with the package

2. **Async Bridge Requirement**: ADR-011 established async `main()` function; console scripts are synchronous entry points that need to bridge to async code

3. **User Experience**: Command name should match package name for discoverability (`pytest-mcp`)

4. **MCP Client Configuration**: Claude Code and other MCP clients expect simple command invocation (e.g., `pytest-mcp` with no arguments)

5. **Standard Python Patterns**: Python packages typically use module:function syntax in `[project.scripts]` (e.g., `"command = package.module:function"`)

## Decision

**We will define a `[project.scripts]` entry point named `pytest-mcp` that invokes a synchronous wrapper function which bridges to the async `main()` using `asyncio.run()`.**

Specifically:
- Add `[project.scripts]` section to pyproject.toml
- Define console script: `pytest-mcp = pytest_mcp.main:cli_main`
- Implement `cli_main()` function in main.py as synchronous wrapper
- `cli_main()` calls `asyncio.run(main())` to bridge sync → async
- async `main()` contains the `stdio_server()` lifecycle logic from ADR-011

## Rationale

### Why This Entry Point Structure?

1. **Standard Python Convention**: `[project.scripts]` is the standard mechanism for installing console commands with Python packages

2. **Clear Command Name**: `pytest-mcp` matches package name, making it discoverable and predictable for users

3. **Minimal Bridging Code**: Single synchronous wrapper function bridges to async; minimal overhead

4. **MCP Client Compatibility**: Simple command invocation with no arguments; works with all MCP clients expecting stdio communication

5. **Clean Separation**: Entry point wrapper lives in main.py alongside async main(); clear module organization

### How the Bridge Works

```python
# Conceptual example - NOT implementation code

# In main.py

# Async main function (ADR-011 lifecycle)
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

# Synchronous entry point wrapper
def cli_main():
    """Console script entry point for pytest-mcp server."""
    asyncio.run(main())
```

**Key Insight**: The wrapper function is trivial—just one line bridging sync → async. All complexity lives in async `main()` where it belongs (ADR-011).

### Why Command Name "pytest-mcp"?

1. **Package Name Match**: Consistent with package name for discoverability
2. **Namespace Clarity**: Clear that this is pytest integration, not core pytest
3. **MCP Convention**: Follows MCP server naming pattern (service-mcp)
4. **No Conflicts**: Distinct from `pytest` command; no shadowing risk

### Integration with MCP Clients

Claude Code configuration example:
```json
{
  "mcpServers": {
    "pytest": {
      "command": "pytest-mcp"
    }
  }
}
```

After `uv tool install pytest-mcp`, the command is available in PATH and MCP clients can invoke it directly.

### Why NOT Alternative Approaches?

**Alternative: Use `__main__.py` Entry Point**
- **Rejected**: Would require `python -m pytest_mcp` invocation instead of clean `pytest-mcp` command
- Less user-friendly; extra verbosity for no benefit
- **Convention**: `[project.scripts]` is standard for CLI tools

**Alternative: Define Entry Point in Separate CLI Module**
- **Rejected**: Single wrapper function doesn't justify separate module
- Adds indirection; harder to find entry point
- **Simplicity**: Wrapper lives alongside async main() in main.py; clear organization

**Alternative: Make main() Synchronous with Manual Event Loop**
- **Rejected**: Would require manually managing asyncio event loop lifecycle
- ADR-011 established async main() with stdio_server() context manager
- **Complexity**: asyncio.run() handles event loop lifecycle automatically

**Alternative: Use Different Command Name (e.g., "pytest_mcp", "pmcp")**
- **Rejected**: Deviates from package name; less discoverable
- Abbreviations like "pmcp" not self-documenting
- **Convention**: Command name typically matches package name

## Consequences

### Positive Outcomes

1. **Standard Installation**: Users install with `uv tool install pytest-mcp`, command immediately available

2. **Clean Configuration**: MCP clients configure with simple `"command": "pytest-mcp"` (no arguments needed)

3. **Minimal Bridging Code**: Single-line wrapper function; zero complexity overhead

4. **Discoverable Command**: Name matches package; users can guess command from package name

5. **No Installation Surprises**: Standard Python packaging; works with pip, uv, pipx, etc.

### Negative Outcomes / Constraints

1. **Command Name Fixed**: Renaming package would require changing command name (affects MCP client configs)
   - **Mitigation**: Package name unlikely to change; established in requirements
   - Breaking change would be major version bump

2. **Entry Point in main.py**: Adds one synchronous function to main.py alongside async code
   - **Trade-off**: Accepted; wrapper is trivial and well-isolated
   - Clear separation: sync wrapper at top, async logic below

3. **No CLI Arguments**: Entry point is stdio server only; no support for `--version`, `--help`, etc.
   - **Current Scope**: Not required for Story 11 (MCP servers use stdio protocol)
   - **Future**: If CLI arguments needed, can add argparse to cli_main()

### Future Decisions Enabled

- **Testing**: Can test entry point by invoking `cli_main()` directly
- **Development Tools**: Can run server locally with `python -m pytest_mcp.main` during development
- **CLI Enhancements**: If needed, can add argument parsing to cli_main() without changing entry point structure

### Future Decisions Constrained

- Command name `pytest-mcp` becomes part of public API; cannot change without breaking user configurations
- Entry point must remain in main.py or require updating pyproject.toml [project.scripts]
- cli_main() must remain synchronous (console script requirement)

## Alternatives Considered

See "Why NOT Alternative Approaches?" section in Rationale for detailed analysis of:
- Using `__main__.py` entry point
- Defining entry point in separate CLI module
- Making main() synchronous with manual event loop
- Using different command name

## References

- ADR-009: MCP SDK Integration (establishes async architecture)
- ADR-010: Tool Routing Architecture (establishes decorator pattern)
- ADR-011: Server Lifecycle Management (establishes async main() with stdio_server())
- [Python Packaging - Entry Points](https://packaging.python.org/en/latest/specifications/entry-points/)
- [Python asyncio.run()](https://docs.python.org/3/library/asyncio-runner.html#asyncio.run)
- REQUIREMENTS_ANALYSIS.md: Story 5.1 (MCP server invocation requirement)
- pyproject.toml: Current configuration (missing [project.scripts])
