"""Tests for main module."""

import tomllib
from pathlib import Path
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
    test_args = {"node_ids": None}
    result = asyncio.run(execute_tests(test_args))

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
    result = asyncio.run(discover_tests(test_args))

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
        asyncio.run(execute_tests(invalid_args))


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
