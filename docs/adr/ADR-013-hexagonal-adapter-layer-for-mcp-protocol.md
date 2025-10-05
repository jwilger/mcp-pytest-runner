# ADR-013: Hexagonal Adapter Layer for MCP Protocol Translation

**Status**: accepted

**Date**: October 5, 2025 (Sunday, accepted)

**Project**: pytest-mcp

## Context

During Story 11 implementation, we discovered a critical architectural pattern: ALL interactions between the MCP protocol and our domain require explicit type translation at the boundary. This isn't just about the `Tool` type conversion issue we initially discovered—it's about establishing a comprehensive hexagonal architecture pattern for every MCP interaction.

The fundamental issue: Our system has two distinct boundaries with the MCP protocol:

1. **Driving Ports (Inbound/Primary - Left Side)**: Where the MCP client drives our application
   - MCP SDK receives requests with `dict[str, Any]` arguments
   - Our domain expects strongly-typed domain models like `ExecuteTestsParams`

2. **Driven Ports (Outbound/Secondary - Right Side)**: Where our domain drives MCP responses
   - Our domain produces response types like `ExecuteTestsResponse`
   - MCP SDK expects protocol-compliant dictionaries and types

Without a clear adapter pattern, we face type mismatches, validation errors, and architectural confusion at every boundary crossing. The initial `Tool` type issue was just the first symptom of a broader architectural need.

Two approaches were considered:
1. **Use MCP SDK types directly throughout**: Let MCP protocol types flow through the entire system
2. **Establish hexagonal architecture with adapters**: Create explicit adapters for ALL MCP boundary crossings

The tension centers on whether MCP protocol concerns should permeate our domain or be isolated at architectural boundaries.

Key factors in this decision:

1. **Bidirectional Boundary Crossings**: Every MCP interaction crosses boundaries in both directions—requests coming in, responses going out—each requiring type translation.

2. **Type Safety Differences**: Domain types are frozen (immutable) with strict validation. SDK types are flexible for protocol compatibility but lack domain guarantees.

3. **Parse Don't Validate Philosophy**: Our domain types enforce constraints at construction time. SDK uses permissive dictionaries that require runtime validation.

4. **SDK Version Evolution**: The MCP SDK may change its type definitions across versions. Direct dependency couples our domain to these changes.

5. **Hexagonal Architecture Principles**: Domain logic should not depend on external protocol libraries. Adapters isolate these concerns.

## Decision

**We will establish a comprehensive hexagonal architecture with explicit adapter functions for ALL MCP protocol boundary crossings, maintaining complete separation between domain and infrastructure concerns.**

This pattern applies to EVERY interaction with the MCP protocol:

### Driving Port Adapters (Inbound/Primary - Left Side)
Convert MCP requests into domain types:
- `from_mcp_params(arguments: dict[str, Any]) -> DomainParams`
- Examples:
  - MCP `arguments` dict → `ExecuteTestsParams` (validated domain type)
  - MCP `arguments` dict → `DiscoverTestsParams` (validated domain type)
  - Any incoming MCP request parameters → corresponding domain types

### Driven Port Adapters (Outbound/Secondary - Right Side)
Convert domain results into MCP responses:
- `to_mcp_response(domain_result: DomainResponse) -> dict[str, Any]`
- Examples:
  - `ExecuteTestsResponse` → MCP-compliant response dictionary
  - `DiscoverTestsResponse` → MCP-compliant response dictionary
  - `domain.Tool` → `mcp.types.Tool`
  - Any domain result → MCP protocol format

### Implementation Structure
- **main.py**: Infrastructure layer containing ALL adapter functions and MCP SDK dependencies
- **domain.py**: Pure domain layer with zero MCP SDK imports or protocol knowledge
- **Clear boundary**: Every MCP interaction goes through an explicit adapter function

## Rationale

### Why Maintain Separate Domain Types?

1. **Stronger Type Guarantees**: Our `domain.Tool` enforces immutability (frozen=True) and required fields at construction time. These constraints catch errors early and prevent invalid states.

2. **Minimal Surface Area**: Domain needs only 3 fields (name, description, inputSchema); SDK type has 8 fields. Why expose unnecessary complexity to domain logic?

3. **Parse Don't Validate Philosophy**: Domain types validate once at construction. SDK types allow mutation and optional fields that could lead to runtime errors.

4. **Domain Independence**: Domain logic shouldn't change when MCP SDK updates. Version changes might alter SDK types but our domain remains stable.

5. **Clear Boundaries**: Hexagonal architecture teaches that domain should be independent of infrastructure. MCP SDK is infrastructure, not domain.

### Why Establish Comprehensive Adapter Pattern?

1. **Bidirectional Type Safety**: Every boundary crossing gets explicit validation and translation:
   - **Inbound**: Untyped MCP dicts → validated domain types (driving ports)
   - **Outbound**: Domain responses → protocol-compliant formats (driven ports)

2. **Single Responsibility**: Each adapter has one job—translate at its specific boundary:
   - Request parameter adapters handle incoming data
   - Response adapters handle outgoing results
   - Tool adapters handle capability discovery

3. **Isolation of Change**: Protocol changes affect only the adapter layer:
   - SDK updates don't ripple through domain logic
   - New MCP features can be adapted without domain modifications
   - Version-specific adapters can coexist if needed

4. **Explicit Architecture**: The hexagonal pattern makes boundaries visible:
   - Clear separation between driving and driven ports
   - Obvious where protocol concerns end and domain begins
   - Easy to trace data flow through the system

5. **Testing Benefits**:
   - Domain logic testable without any MCP SDK mocks
   - Adapter tests are simple transformation validations
   - Can test request and response paths independently

### Key Architectural Insight

**MCP is NOT our domain—test execution is our domain.** MCP is merely the protocol we use to expose our domain to AI agents. This hexagonal architecture establishes clear port classifications:

#### Driving Ports (Primary/Inbound - Left Side)
Where external actors drive our application:
- **Actor**: MCP client (AI agent)
- **Input**: Untyped protocol messages (`dict[str, Any]`)
- **Adapter Role**: Convert protocol requests → validated domain commands
- **Example Flow**: `{"node_ids": ["test_foo"]}` → `ExecuteTestsParams(node_ids=["test_foo"])`

#### Driven Ports (Secondary/Outbound - Right Side)
Where our domain drives external systems:
- **Target**: MCP protocol response channel
- **Output**: Domain results needing protocol formatting
- **Adapter Role**: Convert domain responses → protocol messages
- **Example Flow**: `ExecuteTestsResponse(...)` → `{"exit_code": 0, "summary": {...}}`

This bidirectional adapter pattern ensures infrastructure concerns never leak into domain logic while maintaining type safety at every boundary.

### Why NOT Use SDK Types Directly?

**Alternative: Replace domain.Tool with mcp.types.Tool**
- **Rejected**: Would couple entire domain to MCP SDK version changes
- Loses immutability guarantees (frozen types prevent bugs)
- Loses required field validation (description could be None)
- Domain tests would require MCP SDK imports
- Violates hexagonal architecture principles

**Alternative: Make domain.Tool inherit from mcp.types.Tool**
- **Rejected**: Inheritance creates tight coupling to SDK internals
- Cannot override SDK type behavior (not designed for inheritance)
- Still exposes unnecessary SDK fields to domain
- Changes to SDK base class could break domain types

## Consequences

### Positive Outcomes

1. **Complete Boundary Control**: Every MCP interaction point has explicit adapters:
   - All request parameters validated through driving port adapters
   - All responses formatted through driven port adapters
   - No protocol leakage into domain logic

2. **Clear Hexagonal Architecture**:
   - **Left Side (Driving)**: MCP client → adapters → domain
   - **Right Side (Driven)**: Domain → adapters → MCP protocol
   - **Center (Domain)**: Pure business logic with zero protocol knowledge

3. **Bidirectional Type Safety**:
   - Incoming: Untyped dicts converted to validated domain types
   - Outgoing: Domain types converted to protocol-compliant formats
   - Invalid states impossible at both boundaries

4. **Comprehensive Testability**:
   - Domain tests require zero MCP SDK knowledge
   - Adapter tests validate transformations in isolation
   - Can mock at adapter boundary for integration tests

5. **Architectural Documentation**:
   - Adapter functions explicitly document all boundary crossings
   - Easy to identify all protocol interaction points
   - Clear data flow from request to response

### Negative Outcomes / Constraints

1. **Adapter Proliferation**: Must maintain adapter pairs for every MCP interaction:
   - Driving adapters for each request type
   - Driven adapters for each response type
   - **Mitigation**: Consistent naming pattern (`from_mcp_*`, `to_mcp_*`)
   - **Mitigation**: Adapters are simple transformations, typically 3-10 lines

2. **Conceptual Complexity**: Contributors must understand hexagonal port classifications:
   - Driving vs. driven ports
   - Primary vs. secondary adapters
   - **Mitigation**: Clear documentation in architecture diagrams
   - **Mitigation**: Consistent file organization (all adapters in main.py)

3. **Apparent Duplication**: Request/response types exist in both domain and protocol forms:
   - **Trade-off**: Accepted; each optimized for its context
   - Domain types enforce business rules
   - Protocol types ensure wire compatibility

### Future Decisions Enabled

- Can support multiple MCP SDK versions with version-specific adapters
- Can add protocol-specific validation in adapters without affecting domain
- Can optimize translations if performance becomes a concern
- Can support alternative protocols (HTTP REST, GraphQL) with new adapters

### Future Decisions Constrained

- Must maintain adapter function pairs for ALL MCP interactions (both directions)
- Cannot use MCP SDK types directly in domain layer
- Every new MCP tool requires both driving and driven adapters
- Must ensure adapter tests cover all translation edge cases
- main.py remains the infrastructure layer containing ALL adapter implementations
- New protocol features require adapter updates before domain can utilize them

## Implementation Examples

### Driving Port Adapter (Inbound)
```python
# main.py - Infrastructure Layer
async def handle_execute_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    """MCP handler with driving adapter for request parameters."""
    # DRIVING ADAPTER: Convert MCP arguments to domain type
    params = from_mcp_execute_params(arguments)  # dict → ExecuteTestsParams

    # Pure domain call with validated types
    result = await domain.execute_tests(params)

    # DRIVEN ADAPTER: Convert domain response to MCP format
    return to_mcp_execute_response(result)  # ExecuteTestsResponse → dict

def from_mcp_execute_params(arguments: dict[str, Any]) -> ExecuteTestsParams:
    """Driving port adapter: MCP request → domain type."""
    return ExecuteTestsParams(
        node_ids=arguments.get("node_ids"),
        markers=arguments.get("markers"),
        keywords=arguments.get("keywords"),
        # ... map all parameters
    )
```

### Driven Port Adapter (Outbound)
```python
# main.py - Infrastructure Layer
def to_mcp_tool(domain_tool: domain.Tool) -> mcp.types.Tool:
    """Driven port adapter: domain type → MCP protocol type."""
    return mcp.types.Tool(
        name=domain_tool.name,
        description=domain_tool.description,
        inputSchema=domain_tool.inputSchema,
    )

def to_mcp_execute_response(response: ExecuteTestsResponse) -> dict[str, Any]:
    """Driven port adapter: domain response → MCP format."""
    return {
        "exit_code": response.exit_code,
        "summary": {
            "total": response.summary.total,
            "passed": response.summary.passed,
            # ... map all fields
        },
        "tests": [to_mcp_test_result(t) for t in response.tests],
        "text_output": response.text_output,
    }
```

## Alternatives Considered

### Alternative 1: Use MCP SDK Types Directly
- **Benefits**: No translation code, simpler on surface
- **Drawbacks**: Couples domain to SDK, loses type safety, violates architecture principles
- **Rejected**: Long-term maintenance cost exceeds short-term simplicity gain

### Alternative 2: Generate Domain Types from SDK
- **Benefits**: Automatic synchronization with SDK changes
- **Drawbacks**: Loses ability to enforce stronger constraints, complex generation tooling
- **Rejected**: Generated code lacks domain-specific guarantees we need

### Alternative 3: Shared Interface with Runtime Type Selection
- **Benefits**: Single type definition, runtime flexibility
- **Drawbacks**: Complex type hierarchies, runtime overhead, unclear boundaries
- **Rejected**: Over-engineering for a simple translation problem

## References

- ADR-009: MCP SDK Integration (establishes SDK usage pattern)
- ADR-005: Parameter Validation Strategy (Parse Don't Validate philosophy)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) by Alistair Cockburn
- [Ports and Adapters Pattern](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software)) - Driving vs. Driven port classifications
- STYLE_GUIDE.md: Domain type constraints and validation patterns
- ARCHITECTURE.md: System-wide hexagonal architecture diagram
- Story 2: Initial domain type implementations (ExecuteTestsParams, DiscoverTestsParams)
- Story 11: Discovered need for comprehensive adapter pattern through Tool type mismatch