# ADR-011: Server Lifecycle Management Using stdio_server Context Manager

**Status**: accepted

**Date**: October 3, 2025 (Friday)

**Project**: pytest-mcp

## Context

ADR-009 established using the MCP SDK for transport, and ADR-010 established decorator-based tool routing using `@server.call_tool()`. Story 11 requires implementing the actual server lifecycle—how the MCP server starts, runs the stdio event loop, and shuts down gracefully.

The MCP Python SDK provides a specific lifecycle pattern:

```python
from mcp.server.stdio import stdio_server

# Server instance with decorated tools
server = Server("pytest-mcp")

@server.call_tool()
async def execute_tests(arguments: dict) -> dict:
    # tool implementation

async def main():
    # stdio_server context manager handles lifecycle
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
```

We must decide how to structure server lifecycle to:
1. Initialize the `Server` instance with correct server name
2. Register all decorated tool handlers before starting
3. Start the stdio transport and event loop
4. Handle graceful shutdown when stdio closes
5. Provide clean entry point for users invoking the server

Key considerations:

1. **SDK Lifecycle Pattern**: The `stdio_server()` async context manager handles stdin/stdout stream setup and cleanup automatically

2. **Decorator Registration**: Tools decorated with `@server.call_tool()` must be defined before `server.run()` is called

3. **Async Entry Point**: The MCP SDK requires async/await architecture; entry point must be async main() function

4. **Server Name**: MCP protocol requires servers to identify themselves during initialization handshake

5. **Error Handling**: Server failures during startup or shutdown need proper error propagation

## Decision

**We will use the MCP SDK's stdio_server() async context manager pattern in an async main() function, with decorator registration at module scope.**

Specifically:
- Create module-level `Server` instance: `server = Server("pytest-mcp")`
- Define all `@server.call_tool()` decorated functions at module scope (after Server instance)
- Implement async `main()` function using `async with stdio_server()` pattern
- Call `await server.run(read_stream, write_stream)` within context manager
- Let context manager handle stdio stream lifecycle and cleanup
- Provide console script entry point that calls `asyncio.run(main())`

## Rationale

### Why stdio_server Context Manager Pattern?

1. **SDK Integration**: This is the documented, supported lifecycle pattern from the MCP SDK—guaranteed compatibility

2. **Automatic Resource Management**: Context manager handles stdin/stdout setup, buffering configuration, and cleanup on exit—no manual resource management needed

3. **Clean Shutdown**: Context manager `__aexit__` ensures proper cleanup even if server errors occur during execution

4. **Async-Native**: Pattern uses modern Python async context manager idioms; clean and readable

5. **Stream Isolation**: stdio_server() provides properly configured read/write streams; no need to manage sys.stdin/stdout directly

### Why Module-Scope Decorator Registration?

Decorator registration must happen before `server.run()` is called. Module-scope registration ensures:

1. **Import-Time Registration**: All tools registered when module loads; no missing registration bugs

2. **Clear Declaration**: All server capabilities visible at top of file; easy to audit what server provides

3. **No Dynamic Registration**: Simpler mental model; server capabilities static, not runtime-dependent

4. **SDK Alignment**: Matches SDK's documented pattern and examples

### Server Lifecycle Flow

```python
# Conceptual example - NOT implementation code

# 1. Module scope: Create server instance
server = Server("pytest-mcp")

# 2. Module scope: Define and register tools
@server.call_tool()
async def execute_tests(arguments: dict) -> dict:
    params = ExecuteTestsParams.model_validate(arguments)
    response = domain.execute_tests(params)
    return response.model_dump()

@server.call_tool()
async def discover_tests(arguments: dict) -> dict:
    params = DiscoverTestsParams.model_validate(arguments)
    response = domain.discover_tests(params)
    return response.model_dump()

# 3. Entry point: Async main function
async def main():
    async with stdio_server() as (read_stream, write_stream):
        # Event loop runs until stdio closes
        await server.run(read_stream, write_stream)

# 4. Console script entry point
def cli_main():
    asyncio.run(main())
```

**Key Insight**: The context manager pattern cleanly separates three concerns:
1. **Declaration** (module scope): What the server provides
2. **Initialization** (context manager entry): Setting up stdio transport
3. **Execution** (server.run): Processing requests until shutdown
4. **Cleanup** (context manager exit): Closing streams gracefully

### Why NOT Alternative Approaches?

**Alternative: Manual stdio Stream Management**
- **Rejected**: Would require manually configuring sys.stdin/stdout buffering, line-delimited JSON parsing, stream cleanup
- stdio_server() context manager handles all this complexity automatically
- **Risk**: Incorrect stream configuration breaks MCP protocol compatibility
- **No Benefit**: Reimplementing what SDK provides without advantage

**Alternative: Class-Based Server Wrapper**
- **Rejected**: SDK Server instance is already the main abstraction; wrapping adds indirection
- No clear benefit; decorator pattern works directly with Server instance
- **Complexity**: Additional layer without architectural value
- Doesn't change lifecycle pattern; still need stdio_server() context manager

**Alternative: Synchronous Entry Point with asyncio Wrapper**
- **Rejected**: MCP protocol is inherently async; sync wrapper would add translation layer
- Python's asyncio.run() already provides clean sync → async bridge for console scripts
- **Complexity**: No value in making main() sync when SDK requires async anyway

## Consequences

### Positive Outcomes

1. **SDK-Aligned Lifecycle**: Using documented SDK pattern ensures compatibility and leverages SDK's stream management

2. **Clean Resource Management**: Context manager guarantees proper stdio cleanup even on errors

3. **Clear Shutdown Semantics**: Server runs until stdin closes (client disconnect); no manual termination logic needed

4. **Simple Entry Point**: Single async main() function; straightforward for users and documentation

5. **No Lifecycle Bugs**: SDK handles stream setup, buffering, cleanup—eliminates entire class of lifecycle management bugs

### Negative Outcomes / Constraints

1. **Async Entry Point Required**: Console script must use asyncio.run(); cannot be simple synchronous function
   - **Trade-off**: Accepted; modern Python async patterns are standard
   - User impact minimal; console script invocation identical to sync entry points

2. **Module Import Side Effects**: Tool registration happens at module import time via decorators
   - **Mitigation**: This is standard Python decorator pattern behavior
   - Side effects are idempotent and predictable

3. **SDK Coupling**: Lifecycle tightly coupled to stdio_server() context manager API
   - **Trade-off**: Accepted; using SDK's lifecycle pattern is the point
   - SDK follows semver; breaking changes only in major versions

4. **No Custom Lifecycle Hooks**: Cannot easily add startup/shutdown hooks without wrapping context manager
   - **Current Scope**: Not needed for Story 11 (stateless server has no initialization/cleanup)
   - **Future**: If needed, can wrap stdio_server() in outer context manager for hooks

### Future Decisions Enabled

- **ADR-012**: Entry point structure now clear (async main() with asyncio.run() bridge)
- Console script definition in pyproject.toml follows from this lifecycle pattern
- Future enhancements (logging, metrics) can wrap stdio_server() in outer context manager

### Future Decisions Constrained

- Server lifecycle always uses stdio_server() pattern; cannot switch to manual stream management without losing SDK benefits
- Entry point must be async; cannot convert to synchronous entry point
- Tools must be registered before server.run(); cannot defer registration to runtime

## Alternatives Considered

See "Why NOT Alternative Approaches?" section in Rationale for detailed analysis of:
- Manual stdio stream management
- Class-based server wrapper
- Synchronous entry point with asyncio wrapper

## References

- ADR-009: MCP SDK Integration (establishes SDK usage and async architecture)
- ADR-010: Tool Routing Architecture (establishes decorator-based tool registration)
- [MCP Python SDK - Server Lifecycle](https://github.com/modelcontextprotocol/python-sdk#server-lifecycle)
- [MCP Python SDK - stdio_server](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/stdio.py)
- REQUIREMENTS_ANALYSIS.md: Story 5.1 (server lifecycle requirement)
