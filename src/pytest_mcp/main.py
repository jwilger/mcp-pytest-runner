"""MCP server entry point for pytest-mcp.

This module provides the MCP server initialization and main entry point.
Domain types and workflow functions are defined in the domain module.
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool as McpTool

from pytest_mcp import domain  # noqa: F401 - imported for type availability
from pytest_mcp.domain import DiscoverTestsParams, ExecuteTestsParams

# Module scope: Server instance per ADR-011
server = Server("pytest-mcp")


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
                server_name="pytest-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


@server.call_tool()  # type: ignore[misc]
async def execute_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute pytest tests following ADR-010 pattern.

    Step 1: Parse and validate MCP arguments
    Step 2: Invoke domain workflow function (sync)
    Step 3: Transform domain response to MCP dict
    """
    # Step 1: Parse and validate MCP arguments
    params = ExecuteTestsParams.model_validate(arguments)

    # Step 2: Invoke domain workflow function (sync)
    response = domain.execute_tests(params)

    # Step 3: Transform domain response to MCP dict
    return response.model_dump()


@server.call_tool()  # type: ignore[misc]
async def discover_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    """Discover pytest tests following ADR-010 pattern."""
    params = DiscoverTestsParams.model_validate(arguments)
    response = domain.discover_tests(params)
    return response.model_dump()


if __name__ == "__main__":
    asyncio.run(main())
