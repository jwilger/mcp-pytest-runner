"""MCP server entry point for pytest-mcp.

This module provides the MCP server initialization and main entry point.
Domain types and workflow functions are defined in the domain module.

Modified: 2025-10-06 - Unified tool handler implementation
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool as McpTool

from mcp_pytest_runner import domain  # noqa: F401 - imported for type availability
from mcp_pytest_runner.domain import DiscoverTestsParams, ExecuteTestsParams

# Module scope: Server instance per ADR-011
server = Server("mcp-pytest-runner")


def to_mcp_tool(domain_tool: domain.Tool) -> McpTool:
    """Convert domain.Tool to mcp.types.Tool per ADR-013 adapter pattern.

    Driven port adapter: Converts domain types to MCP SDK types for protocol compliance.

    Args:
        domain_tool: Domain tool definition

    Returns:
        MCP SDK Tool instance
    """
    return McpTool(
        name=domain_tool.name,
        description=domain_tool.description,
        inputSchema=domain_tool.inputSchema,
    )


@server.list_tools()  # type: ignore[misc, no-untyped-call]
async def list_available_tools() -> list[McpTool]:
    """List available MCP tools following ADR-010 pattern."""
    domain_tools = domain.list_tools()
    return [to_mcp_tool(tool) for tool in domain_tools]


def cli_main() -> None:
    """Console script entry point for pytest-mcp server."""
    asyncio.run(main())


async def main() -> None:
    """Start the MCP server using stdio_server lifecycle per ADR-011."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-pytest-runner",
                server_version="0.2.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


@server.call_tool()  # type: ignore[misc]
async def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Unified MCP tool handler - routes to appropriate domain function based on tool name.

    MCP SDK only supports ONE @server.call_tool() handler. This function routes to the
    appropriate domain workflow based on the tool name parameter.

    Step 1: Route based on tool name
    Step 2: Validate arguments with appropriate Pydantic model
    Step 3: Call appropriate domain workflow function
    Step 4: Transform domain response to MCP dict
    """
    if name == "execute_tests":
        execute_params = ExecuteTestsParams.model_validate(arguments)
        execute_response = domain.execute_tests(execute_params)
        return execute_response.model_dump()
    elif name == "discover_tests":
        discover_params = DiscoverTestsParams.model_validate(arguments)
        discover_response = domain.discover_tests(discover_params)
        return discover_response.model_dump()
    else:
        raise ValueError(f"Unknown tool: {name}")


# Backward compatibility aliases for tests
async def execute_tests(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Backward compatibility wrapper - delegates to handle_tool_call."""
    return await handle_tool_call(name, arguments)  # type: ignore[no-any-return]


async def discover_tests(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Backward compatibility wrapper - delegates to handle_tool_call."""
    return await handle_tool_call(name, arguments)  # type: ignore[no-any-return]


if __name__ == "__main__":
    asyncio.run(main())
