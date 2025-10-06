"""Tests for main module."""

import tomllib
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest_mcp.main import main


def find_pyproject_toml(start_path: Path) -> Path:
    """Walk up parent directories to find pyproject.toml."""
    current = start_path.resolve()
    while True:
        candidate = current / "pyproject.toml"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            raise FileNotFoundError("pyproject.toml not found in any parent directory")
        current = current.parent


def test_cli_main_function_exists() -> None:
    """Verify cli_main() entry point exists per ADR-012."""
    from pytest_mcp.main import cli_main

    assert callable(cli_main)


@patch("pytest_mcp.main.asyncio.run")
def test_cli_main_calls_asyncio_run_with_main(mock_asyncio_run: MagicMock) -> None:
    """Verify cli_main() calls asyncio.run(main()) per ADR-012."""
    from pytest_mcp.main import cli_main

    cli_main()

    assert mock_asyncio_run.called


def test_console_script_entry_point_configured() -> None:
    """Verify pyproject.toml defines pytest-mcp console script per ADR-012."""
    pyproject_path = find_pyproject_toml(Path(__file__).parent)
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    scripts = config.get("project", {}).get("scripts", {})
    assert "pytest-mcp" in scripts


def test_server_instance_exists() -> None:
    """Verify Server instance exists at module scope per ADR-011."""
    from mcp.server import Server

    from pytest_mcp.main import server

    assert isinstance(server, Server)


@patch("pytest_mcp.main.stdio_server")
@patch("pytest_mcp.main.server.run", new_callable=AsyncMock)
def test_main_uses_stdio_server_lifecycle(
    mock_server_run: AsyncMock,
    mock_stdio_server: MagicMock,
) -> None:
    """Verify main() uses stdio_server() lifecycle per ADR-011."""
    import asyncio

    # Mock stdio_server context manager
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    mock_stdio_server.return_value.__aenter__.return_value = (
        mock_read_stream,
        mock_write_stream,
    )

    # Call main()
    asyncio.run(main())

    # Verify stdio_server was used
    mock_stdio_server.assert_called_once()

    # Verify server.run was called
    mock_server_run.assert_called_once()
    call_args = mock_server_run.call_args[0]
    assert call_args[0] == mock_read_stream
    assert call_args[1] == mock_write_stream
    # Third arg is InitializationOptions - just verify it's not None
    assert call_args[2] is not None


@patch("pytest_mcp.main.domain.execute_tests")
def test_execute_tests_tool_handler_exists(
    mock_domain_execute: MagicMock,
) -> None:
    """Verify execute_tests tool handler follows ADR-010 pattern.

    The handler must:
    1. Accept MCP arguments dict
    2. Validate using ExecuteTestsParams
    3. Call domain.execute_tests() with validated params
    4. Return response.model_dump()
    """
    import asyncio

    from pytest_mcp.domain import ExecuteTestsParams, ExecuteTestsResponse, ExecutionSummary
    from pytest_mcp.main import execute_tests

    # Mock domain function to return test response
    mock_response = ExecuteTestsResponse(
        exit_code=0,
        summary=ExecutionSummary(total=0, passed=0, failed=0, errors=0, skipped=0, duration=0.0),
        tests=[],
        text_output="",
    )
    mock_domain_execute.return_value = mock_response

    # Call the tool handler with MCP arguments
    test_args: dict[str, Any] = {}  # Will use default=[]
    result = asyncio.run(execute_tests(name="execute_tests", arguments=test_args))

    # Verify domain function called with validated params
    assert mock_domain_execute.called
    called_params = mock_domain_execute.call_args[0][0]
    assert isinstance(called_params, ExecuteTestsParams)

    # Verify result is dict (model_dump() called)
    assert isinstance(result, dict)


@patch("pytest_mcp.main.domain.discover_tests")
def test_discover_tests_tool_handler_exists(
    mock_domain_discover: MagicMock,
) -> None:
    """Verify discover_tests tool handler follows ADR-010 pattern.

    The handler must:
    1. Accept MCP arguments dict
    2. Validate using DiscoverTestsParams
    3. Call domain.discover_tests() with validated params
    4. Return response.model_dump()
    """
    import asyncio

    from pytest_mcp.domain import (
        DiscoveredTest,
        DiscoverTestsParams,
        DiscoverTestsResponse,
    )
    from pytest_mcp.main import discover_tests

    # Mock domain function to return test response
    mock_response = DiscoverTestsResponse(
        tests=[
            DiscoveredTest(
                node_id="tests/test_sample.py::test_example",
                module="tests.test_sample",
                function="test_example",
                file="tests/test_sample.py",
                line=None,
            )
        ],
        count=1,
        collection_errors=[],
    )
    mock_domain_discover.return_value = mock_response

    # Call the tool handler with MCP arguments
    test_args = {"path": None, "pattern": None}
    result = asyncio.run(discover_tests(name="discover_tests", arguments=test_args))

    # Verify domain function called with validated params
    assert mock_domain_discover.called
    called_params = mock_domain_discover.call_args[0][0]
    assert isinstance(called_params, DiscoverTestsParams)

    # Verify result is dict (model_dump() called)
    assert isinstance(result, dict)


def test_tool_handler_raises_validation_error_for_invalid_arguments() -> None:
    """Verify tool handlers raise ValidationError for invalid arguments.

    ADR-010 pattern uses Pydantic model_validate() which raises ValidationError
    for invalid input. This test verifies the error propagates correctly.
    """
    import asyncio

    import pytest
    from pydantic import ValidationError

    from pytest_mcp.main import execute_tests

    # Invalid arguments - execute_tests doesn't accept 'invalid_field'
    invalid_args = {"invalid_field": "bad_value"}

    # Should raise ValidationError
    with pytest.raises(ValidationError):
        asyncio.run(execute_tests(name="execute_tests", arguments=invalid_args))


@patch("pytest_mcp.main.stdio_server")
@patch("pytest_mcp.main.server.run", new_callable=AsyncMock)
def test_server_advertises_tools_capability(
    mock_server_run: AsyncMock,
    mock_stdio_server: MagicMock,
) -> None:
    """Verify that the MCP server advertises the tools capability to clients.

    This test ensures that when the server is started, it sets the tools capability
    in the InitializationOptions, allowing MCP clients to discover available tools.

    The test asserts that capabilities.tools is set (not None) when passed to
    InitializationOptions during the server.run() call.
    """
    import asyncio

    from mcp.types import ServerCapabilities

    # Mock stdio_server context manager
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    mock_stdio_server.return_value.__aenter__.return_value = (
        mock_read_stream,
        mock_write_stream,
    )

    # Call main()
    asyncio.run(main())

    # Verify server.run was called
    mock_server_run.assert_called_once()

    # Extract InitializationOptions (third argument to server.run)
    init_options = mock_server_run.call_args[0][2]
    assert init_options is not None, "InitializationOptions should be passed to server.run()"

    # Extract capabilities from InitializationOptions
    capabilities = init_options.capabilities
    assert isinstance(capabilities, ServerCapabilities), (
        "capabilities should be ServerCapabilities instance"
    )

    # CRITICAL ASSERTION: Verify tools capability is advertised
    assert capabilities.tools is not None, (
        "capabilities.tools must be set to advertise tools to MCP clients"
    )


@patch("pytest_mcp.main.stdio_server")
@patch("pytest_mcp.main.server.run", new_callable=AsyncMock)
def test_initialization_uses_server_get_capabilities(
    mock_server_run: AsyncMock,
    mock_stdio_server: MagicMock,
) -> None:
    """Verify InitializationOptions uses server.get_capabilities() for proper tool discovery.

    CRITICAL BUG TEST: Manually constructing ServerCapabilities leaves tools.listChanged=None,
    which causes MCP clients to report hasTools=false. The SDK's server.get_capabilities()
    automatically sets tools.listChanged=False when tools are registered.

    This test verifies that:
    1. InitializationOptions.capabilities comes from server.get_capabilities()
    2. capabilities.tools.listChanged is set to False (not None)
    3. MCP clients can properly detect available tools
    """
    import asyncio

    # Mock stdio_server context manager
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    mock_stdio_server.return_value.__aenter__.return_value = (
        mock_read_stream,
        mock_write_stream,
    )

    # Call main()
    asyncio.run(main())

    # Extract InitializationOptions (third argument to server.run)
    init_options = mock_server_run.call_args[0][2]
    capabilities = init_options.capabilities

    # CRITICAL ASSERTION: Verify tools.listChanged is False (not None)
    # This proves server.get_capabilities() was used instead of manual construction
    assert capabilities.tools.listChanged is False, (
        "capabilities.tools.listChanged must be False (set by server.get_capabilities()) "
        "to enable proper MCP client tool discovery. Currently None indicates manual "
        "ServerCapabilities construction was used instead of server.get_capabilities()"
    )


@patch("pytest_mcp.main.domain.list_tools")
def test_list_tools_handler_exists_and_returns_tool_definitions(
    mock_domain_list_tools: MagicMock,
) -> None:
    """Verify MCP server has @server.list_tools() handler that returns MCP tool definitions.

    Per ADR-013, the handler uses driven port adapter to convert domain.Tool → mcp.types.Tool.

    The handler must:
    1. Be decorated with @server.list_tools()
    2. Call domain.list_tools() to get domain tool definitions
    3. Use adapter to convert domain.Tool → mcp.types.Tool
    4. Return list[mcp.types.Tool] for MCP SDK

    Per MCP protocol, when client sends tools/list request, server must respond with
    list of mcp.types.Tool objects containing name, description, and inputSchema.
    """
    import asyncio

    from mcp.types import Tool as McpTool

    from pytest_mcp.domain import Tool as DomainTool
    from pytest_mcp.main import list_available_tools

    # Mock domain.list_tools() to return domain tool definitions
    mock_tools = [
        DomainTool(
            name="execute_tests",
            description="Execute pytest tests",
            inputSchema={"type": "object", "properties": {}},
        ),
        DomainTool(
            name="discover_tests",
            description="Discover pytest tests",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
    mock_domain_list_tools.return_value = mock_tools

    # Call the MCP handler
    result = asyncio.run(list_available_tools())

    # Verify domain function was called
    assert mock_domain_list_tools.called, (
        "list_available_tools handler must call domain.list_tools()"
    )

    # Verify result is list of mcp.types.Tool (after adapter conversion)
    assert isinstance(result, list), "Handler must return list"
    assert len(result) == 2, "Handler must return both tools"
    assert all(isinstance(tool, McpTool) for tool in result), (
        "Handler must return list[mcp.types.Tool] per ADR-013 adapter pattern"
    )


@patch("pytest_mcp.main.domain.list_tools")
def test_list_tools_uses_adapter_to_convert_domain_to_mcp_types(
    mock_domain_list_tools: MagicMock,
) -> None:
    """Verify list_available_tools() uses adapter to convert domain.Tool → mcp.types.Tool.

    Per ADR-013 (Hexagonal Adapter Layer), ALL MCP protocol interactions require explicit
    adapters. This is a DRIVEN PORT adapter (outbound/secondary):
    - Domain produces: list[domain.Tool]
    - Adapter converts: domain.Tool → mcp.types.Tool
    - MCP SDK expects: list[mcp.types.Tool]

    The test verifies:
    1. Domain layer returns domain.Tool objects
    2. Adapter function exists to convert domain.Tool → mcp.types.Tool
    3. MCP handler uses adapter to return mcp.types.Tool instances

    This test will FAIL because:
    - Current implementation directly returns domain.Tool objects
    - No adapter function exists yet
    - MCP SDK receives incompatible Pydantic BaseModel instead of mcp.types.Tool
    """
    import asyncio

    from mcp.types import Tool as McpTool

    from pytest_mcp.domain import Tool as DomainTool
    from pytest_mcp.main import list_available_tools

    # Mock domain.list_tools() to return domain.Tool objects
    mock_tools = [
        DomainTool(
            name="execute_tests",
            description="Execute pytest tests",
            inputSchema={"type": "object", "properties": {}},
        ),
        DomainTool(
            name="discover_tests",
            description="Discover pytest tests",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
    mock_domain_list_tools.return_value = mock_tools

    # Call the MCP handler
    result = asyncio.run(list_available_tools())

    # CRITICAL ASSERTION: Verify adapter converted domain.Tool → mcp.types.Tool
    # Per ADR-013, driven port adapters must convert domain types to MCP protocol types
    assert isinstance(result, list), "Handler must return list"
    assert len(result) == 2, "Handler must return both tools"

    # Verify each tool is mcp.types.Tool instance (not domain.Tool)
    for i, tool in enumerate(result):
        assert isinstance(tool, McpTool), (
            f"Tool {i} must be mcp.types.Tool instance per ADR-013 adapter pattern. "
            f"Got {type(tool).__name__} instead. "
            "Driven port adapters (to_mcp_*) must convert domain types to MCP SDK types."
        )


@patch("pytest_mcp.main.domain.execute_tests")
def test_execute_tests_handler_accepts_name_and_arguments_parameters(
    mock_domain_execute: MagicMock,
) -> None:
    """Verify execute_tests handler accepts both name and arguments parameters.

    MCP SDK's @server.call_tool() decorator passes both name and arguments to handlers:
    - name: str - The tool name being invoked
    - arguments: dict[str, Any] - The tool arguments

    This test verifies the handler signature matches MCP SDK requirements and doesn't
    raise TypeError about the number of positional arguments.
    """
    import asyncio

    from pytest_mcp.domain import ExecuteTestsResponse, ExecutionSummary
    from pytest_mcp.main import execute_tests

    # Mock domain function to return test response
    mock_response = ExecuteTestsResponse(
        exit_code=0,
        summary=ExecutionSummary(total=0, passed=0, failed=0, errors=0, skipped=0, duration=0.0),
        tests=[],
        text_output="",
    )
    mock_domain_execute.return_value = mock_response

    # Call handler with both name and arguments as MCP SDK does
    test_args: dict[str, Any] = {}  # Will use default=[]
    result = asyncio.run(execute_tests(name="execute_tests", arguments=test_args))

    # CRITICAL ASSERTION: Handler should not raise TypeError about argument count
    assert isinstance(result, dict)


@patch("pytest_mcp.main.domain.discover_tests")
def test_discover_tests_handler_accepts_name_and_arguments_parameters(
    mock_domain_discover: MagicMock,
) -> None:
    """Verify discover_tests handler accepts both name and arguments parameters.

    MCP SDK's @server.call_tool() decorator passes both name and arguments to handlers:
    - name: str - The tool name being invoked
    - arguments: dict[str, Any] - The tool arguments

    This test verifies the handler signature matches MCP SDK requirements and doesn't
    raise TypeError about the number of positional arguments.
    """
    import asyncio

    from pytest_mcp.domain import (
        DiscoveredTest,
        DiscoverTestsResponse,
    )
    from pytest_mcp.main import discover_tests

    # Mock domain function to return test response
    mock_response = DiscoverTestsResponse(
        tests=[
            DiscoveredTest(
                node_id="tests/test_sample.py::test_example",
                module="tests.test_sample",
                function="test_example",
                file="tests/test_sample.py",
                line=None,
            )
        ],
        count=1,
        collection_errors=[],
    )
    mock_domain_discover.return_value = mock_response

    # Call handler with both name and arguments as MCP SDK does
    test_args = {"path": None, "pattern": None}
    result = asyncio.run(discover_tests(name="discover_tests", arguments=test_args))

    # CRITICAL ASSERTION: Handler should not raise TypeError about argument count
    assert isinstance(result, dict)


@patch("pytest_mcp.main.domain.execute_tests")
@patch("pytest_mcp.main.domain.discover_tests")
def test_single_tool_handler_routes_to_correct_domain_function(
    mock_domain_discover: MagicMock,
    mock_domain_execute: MagicMock,
) -> None:
    """Verify there is ONE tool handler that routes to correct domain function based on name.

    CRITICAL BUG: MCP SDK only supports ONE @server.call_tool() handler.
    Multiple @server.call_tool() decorators overwrite each other - only the LAST one is registered.

    Current code has TWO decorators (execute_tests, discover_tests), so only discover_tests
    is actually being called by the MCP SDK, causing execute_tests tool calls to fail.

    SOLUTION: Single unified handler that routes based on the 'name' parameter:
    - When name='execute_tests': validate with ExecuteTestsParams, call domain.execute_tests()
    - When name='discover_tests': validate with DiscoverTestsParams, call domain.discover_tests()

    This test verifies the single handler exists and routes correctly to both domain functions.
    """
    import asyncio

    from pytest_mcp.domain import (
        DiscoveredTest,
        DiscoverTestsResponse,
        ExecuteTestsResponse,
        ExecutionSummary,
    )
    from pytest_mcp.main import handle_tool_call

    # Mock execute_tests domain response
    mock_execute_response = ExecuteTestsResponse(
        exit_code=0,
        summary=ExecutionSummary(total=0, passed=0, failed=0, errors=0, skipped=0, duration=0.5),
        tests=[],
        text_output="1 passed",
    )
    mock_domain_execute.return_value = mock_execute_response

    # Mock discover_tests domain response
    mock_discover_response = DiscoverTestsResponse(
        tests=[
            DiscoveredTest(
                node_id="tests/test_sample.py::test_example",
                module="tests.test_sample",
                function="test_example",
                file="tests/test_sample.py",
                line=None,
            )
        ],
        count=1,
        collection_errors=[],
    )
    mock_domain_discover.return_value = mock_discover_response

    # Test 1: Call handler with execute_tests tool name
    execute_args = {"node_ids": ["tests/test_sample.py::test_example"]}
    execute_result = asyncio.run(handle_tool_call(name="execute_tests", arguments=execute_args))

    # Verify execute_tests was routed correctly
    assert mock_domain_execute.called, "Handler must route execute_tests to domain.execute_tests()"
    assert isinstance(execute_result, dict), "Handler must return dict from domain response"
    assert execute_result["exit_code"] == 0

    # Test 2: Call handler with discover_tests tool name
    discover_args = {"path": None, "pattern": None}
    discover_result = asyncio.run(handle_tool_call(name="discover_tests", arguments=discover_args))

    # Verify discover_tests was routed correctly
    assert mock_domain_discover.called, (
        "Handler must route discover_tests to domain.discover_tests()"
    )
    assert isinstance(discover_result, dict), "Handler must return dict from domain response"
    assert discover_result["count"] == 1
