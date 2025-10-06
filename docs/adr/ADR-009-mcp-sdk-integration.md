# ADR-009: MCP SDK Integration for JSON-RPC Transport

**Status**: accepted

**Date**: October 3, 2025 (Friday)

**Project**: pytest-mcp

## Context

Stories 1-4 delivered complete workflow functions (`execute_tests`, `discover_tests`, `initialize_server`, `list_tools`) and domain types, but the MCP server cannot be used because there is no transport layer. AI agents expect MCP servers to communicate via JSON-RPC 2.0 over stdio following the Model Context Protocol specification.

The MCP Python SDK (mcp>=1.16.0, already in dependencies) provides the official implementation of:
- JSON-RPC 2.0 message framing over stdio
- MCP protocol initialization handshake
- Tool registration and capability advertisement
- Request routing and response serialization
- Error handling per MCP specification

We must decide how to integrate the MCP SDK to provide this transport layer while preserving our tested workflow functions unchanged.

Key considerations:

1. **SDK Compliance**: MCP clients expect servers to follow the MCP specification exactly. Custom JSON-RPC implementations risk compatibility issues.

2. **Integration Surface**: Our domain.py workflow functions return domain types (ExecuteTestsResponse, DiscoverTestsResponse). The MCP SDK expects async functions returning MCP SDK types.

3. **Control vs Convenience**: The MCP SDK provides high-level server abstractions that handle protocol details automatically, but this may constrain how we structure our code.

4. **Error Model Alignment**: Our domain functions raise ProtocolError for validation failures and return structured error responses for pytest failures. MCP SDK has its own error handling conventions.

## Decision

**We will use the MCP Python SDK directly for all protocol transport, accepting its async server model and wrapping our workflow functions with thin async adapters.**

Specifically:
- Import `mcp.server.Server` for the stdio server implementation
- Import `mcp.server.stdio.stdio_server` for stdio transport initialization
- Create async adapter functions that invoke our workflow functions and transform domain types to MCP SDK response types
- Register tools using the SDK's `@server.call_tool` decorator pattern
- Accept the SDK's async/await model as the entry point architecture

## Rationale

### Why Direct MCP SDK Usage?

1. **Protocol Compliance Guaranteed**: The SDK is the reference implementation from Anthropic. Using it ensures compatibility with all MCP clients (Claude Code, etc.) without protocol interpretation risks.

2. **Future-Proof**: MCP specification evolves; the SDK updates handle protocol changes automatically. Custom JSON-RPC would require manual protocol tracking.

3. **Battle-Tested Error Handling**: The SDK handles malformed requests, protocol version mismatches, and edge cases already validated by Anthropic's testing.

4. **Zero Serialization Code**: The SDK handles JSON-RPC message framing, stdio buffering, and newline-delimited JSON formatting. We would need to reimplement all of this in a custom approach.

5. **Tool Registration Ergonomics**: The SDK's decorator pattern (`@server.call_tool`) provides clean, declarative tool registration with automatic parameter schema generation from type hints.

### How We Preserve Domain Purity

The adapter layer will be thin and focused:

```python
# Thin adapter in main.py (conceptual example - NOT implementation code)
@server.call_tool()
async def execute_tests(arguments: dict) -> dict:
    # Parse MCP arguments dict → domain params
    params = ExecuteTestsParams.model_validate(arguments)

    # Invoke pure workflow function
    response = domain.execute_tests(params)

    # Transform domain response → MCP dict
    return response.model_dump()
```

This keeps domain.py unchanged (constraint from Story 5) while providing MCP compatibility.

### Why NOT Custom JSON-RPC Implementation?

**Alternative: Build Custom JSON-RPC 2.0 Handler**
- **Rejected**: Reimplementing JSON-RPC 2.0 is significant work (message framing, request/response correlation, batch support, error codes)
- MCP has specific conventions beyond base JSON-RPC (initialization handshake, capability negotiation, tool schemas)
- Custom implementation would need extensive testing against multiple MCP clients
- Maintenance burden: Must track MCP specification changes manually
- **Risk**: Protocol incompatibility bugs affecting production usage

**Alternative: Lightweight JSON-RPC Library + MCP Layer**
- **Rejected**: Still requires implementing MCP-specific protocol on top of generic JSON-RPC
- Adds dependency beyond official SDK without clear benefit
- Splits protocol responsibility across two layers (library + our code)
- **No advantage** over using the purpose-built MCP SDK

### Async Model Trade-Off

**Trade-off Accepted**: The MCP SDK requires async/await architecture. Our workflow functions are synchronous.

**Why This Is Fine**:
- Adapter layer handles async → sync bridge with minimal overhead
- Workflow functions remain testable synchronously (no async test complexity)
- MCP protocol is inherently async (clients expect async responses), so this aligns with reality
- Python's `asyncio.to_thread()` can offload blocking operations if needed (though subprocess calls already async-compatible)

## Consequences

### Positive Outcomes

1. **Protocol Compatibility**: Guaranteed compatibility with all MCP clients using the reference implementation.

2. **Reduced Implementation Work**: SDK handles JSON-RPC framing, stdio transport, error formatting, protocol negotiation—no custom code needed.

3. **Maintainability**: MCP protocol updates delivered via SDK dependency updates; no manual protocol tracking.

4. **Clear Separation**: Adapter layer explicitly separates transport concerns (MCP SDK) from domain logic (workflow functions).

5. **Reduced Testing Burden**: Don't need to test JSON-RPC message framing, only test adapter transformations and domain logic.

### Negative Outcomes / Constraints

1. **SDK Dependency**: Coupled to MCP SDK's API surface; SDK breaking changes require adapter updates.
   - **Mitigation**: SDK follows semver; breaking changes only in major versions
   - Pin to compatible version range in pyproject.toml

2. **Async Entrypoint Required**: main.py must use async/await; cannot be simple synchronous function.
   - **Trade-off**: Accepted; modern Python async patterns are well-understood
   - Adapter layer is small and straightforward

3. **Type Transformation Layer**: Must transform between domain types (Pydantic) and MCP SDK types (dicts/SDK objects).
   - **Benefit**: Explicit transformation makes boundaries clear
   - Pydantic's `model_dump()` and `model_validate()` handle most complexity

4. **SDK Learning Curve**: Contributors must understand MCP SDK patterns.
   - **Mitigation**: SDK is well-documented; adapter layer is small and clear
   - Most contributors work on domain.py, which is SDK-independent

### Future Decisions Enabled

- **ADR-010**: Tool routing architecture can use SDK's decorator pattern for registration
- **ADR-011**: Server lifecycle follows SDK's async server pattern with stdio_server()
- **ADR-012**: Entry point structure determined by SDK's async requirements

### Future Decisions Constrained

- Cannot remove MCP SDK dependency without replacing entire transport layer
- Adapter layer must maintain domain type ↔ MCP dict transformations
- Server initialization must follow SDK's async server lifecycle patterns

## Alternatives Considered

See "Why NOT Custom JSON-RPC Implementation?" section in Rationale for detailed analysis of:
- Custom JSON-RPC 2.0 handler implementation
- Lightweight JSON-RPC library with custom MCP layer

## References

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- ADR-001: MCP Protocol Selection (establishes MCP as the integration approach)
- ADR-002: Stateless Architecture (workflow functions remain stateless, adapter layer doesn't change this)
- REQUIREMENTS_ANALYSIS.md: Story 5.1 (MCP Protocol Transport requirement)
- pyproject.toml: `mcp>=1.16.0` already in dependencies
