# ADR-010: Tool Routing Architecture Using MCP SDK Decorators

**Status**: accepted

**Date**: October 3, 2025 (Friday)

**Project**: pytest-mcp

## Context

ADR-009 established using the MCP Python SDK for transport with thin async adapters. Story 11 requires implementing the actual tool routing—mapping MCP tool names ("execute_tests", "discover_tests") to our domain workflow functions.

The MCP SDK provides a specific tool registration pattern using decorators:

```python
@server.call_tool()
async def tool_name(arguments: dict) -> dict:
    # handler implementation
```

We must decide how to structure tool routing to:
1. Connect MCP tool name strings to domain workflow functions
2. Transform between MCP dict arguments and Pydantic domain types
3. Handle async/sync boundary (SDK requires async, domain is sync)
4. Maintain clear separation between transport and domain logic

Key considerations:

1. **SDK Patterns**: The `@server.call_tool()` decorator automatically registers tools and handles routing by function name matching
2. **Type Transformation**: MCP sends `dict` arguments; domain expects Pydantic types (ExecuteTestsParams, DiscoverTestsParams)
3. **Error Handling**: Pydantic ValidationError needs MCP-compatible error responses
4. **Separation of Concerns**: Tool routing code should be separate from domain logic (domain.py unchanged per Story 5 constraint)

## Decision

**We will use the MCP SDK's decorator pattern for declarative tool registration with one async adapter function per MCP tool.**

Specifically:
- Create async adapter functions in main.py decorated with `@server.call_tool()`
- Function names match MCP tool names exactly ("execute_tests", "discover_tests")
- Each adapter performs three steps: parse arguments, invoke domain function, return response
- Use Pydantic's `model_validate()` for dict → domain type transformation
- Use Pydantic's `model_dump()` for domain type → dict transformation
- Place all tool routing logic in main.py, keeping domain.py unchanged

## Rationale

### Why SDK Decorator Pattern?

1. **Automatic Registration**: The `@server.call_tool()` decorator handles tool registration automatically—no manual routing table maintenance

2. **Name-Based Routing**: Tool name matches function name; SDK routes requests by simple name lookup—zero routing code needed

3. **Declarative Clarity**: Each tool adapter is self-contained and clearly visible in code; no indirection through registration functions

4. **SDK Integration**: Using the SDK's intended pattern ensures compatibility and leverages SDK's internal optimizations

5. **Type Safety at Boundary**: Pydantic validation at adapter entry ensures only valid domain types reach workflow functions

### How Adapters Maintain Domain Purity

Each adapter follows a consistent three-step pattern:

```python
# Conceptual example - NOT implementation code
@server.call_tool()
async def execute_tests(arguments: dict) -> dict:
    # Step 1: Parse and validate MCP arguments
    params = ExecuteTestsParams.model_validate(arguments)

    # Step 2: Invoke domain workflow function (sync)
    response = domain.execute_tests(params)

    # Step 3: Transform domain response to MCP dict
    return response.model_dump()
```

This keeps domain.py completely unaware of MCP protocol while maintaining type safety.

### Error Handling Strategy

Pydantic ValidationError from `model_validate()` will be caught and transformed to MCP error responses:
- Validation errors indicate client sent invalid arguments
- Error response includes field-level validation details
- AI agents receive actionable error messages for correction

### Why NOT Alternative Approaches?

**Alternative: Dynamic Registration with Routing Table**
- **Rejected**: Requires maintaining separate tool name → handler mapping
- More indirection; harder to trace tool name to implementation
- No benefit over decorator approach which SDK provides
- **Complexity**: Additional registration code without clear advantage

**Alternative: Single Mega-Handler with Switch Statement**
- **Rejected**: Single function handling all tools would violate single responsibility
- Hard to test individual tool handlers in isolation
- Pattern doesn't match SDK's decorator approach
- **Maintainability**: Adding new tools requires modifying switch logic

**Alternative: Class-Based Handlers**
- **Rejected**: SDK decorator pattern is function-based; class pattern would add unnecessary abstraction
- No clear benefit for our simple adapter use case
- **Complexity**: More boilerplate without architectural gain

## Consequences

### Positive Outcomes

1. **Clear Routing**: Tool name matches function name; zero ambiguity in routing logic

2. **Type Safety**: Pydantic validation ensures only valid domain types reach workflow functions

3. **Easy Testing**: Each adapter function testable independently with mock domain functions

4. **Simple Additions**: New tools added by creating new decorated async functions—no routing table updates needed

5. **SDK Alignment**: Using SDK's intended pattern ensures compatibility and future-proof design

### Negative Outcomes / Constraints

1. **Function Name Coupling**: Tool names must match function names exactly; renaming requires updating both
   - **Mitigation**: Tool names defined by MCP protocol (stable); unlikely to change

2. **Adapter Duplication**: Each tool needs its own adapter function; some repetitive structure
   - **Trade-off**: Accepted; clarity and testability worth minimal duplication
   - Each adapter has tool-specific validation and error handling

3. **Async/Sync Boundary**: Every adapter crosses async → sync boundary
   - **Minor Overhead**: Single function call; negligible performance impact
   - Python's async/await well-optimized for this pattern

### Future Decisions Enabled

- **ADR-011**: Server lifecycle can now initialize `Server` instance and register decorated tools
- **ADR-012**: Entry point structure determined (async main calling SDK's stdio_server)
- Tool schema generation can leverage Pydantic models (future enhancement)

### Future Decisions Constrained

- Tool routing always uses decorator pattern; cannot switch to dynamic registration without SDK incompatibility
- Adapter layer required for all new tools; cannot bypass for direct domain access
- main.py contains all routing logic; separation must be maintained

## Alternatives Considered

See "Why NOT Alternative Approaches?" section in Rationale for detailed analysis of:
- Dynamic registration with routing table
- Single mega-handler with switch statement
- Class-based handler approach

## References

- ADR-009: MCP SDK Integration (establishes SDK usage and async adapter pattern)
- ADR-002: Stateless Architecture (adapters remain stateless, just transformation logic)
- [MCP Python SDK - Server Tools](https://github.com/modelcontextprotocol/python-sdk#tools)
- REQUIREMENTS_ANALYSIS.md: Story 5.1 (tool routing requirement)
- domain.py: `execute_tests()`, `discover_tests()` workflow functions
