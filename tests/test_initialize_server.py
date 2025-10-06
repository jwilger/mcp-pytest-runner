"""Tests for MCP server initialization (Story 1).

Outside-In TDD: Start with highest-level acceptance test for successful initialization.
Test the workflow function directly before drilling down to components.
"""

import pytest

from mcp_pytest_runner.domain import (
    ProtocolValidationError,
    initialize_server,
)


def test_initialize_server_succeeds_with_supported_protocol_version() -> None:
    """Verify initialize_server returns valid response for supported protocol version.

    Acceptance Criteria (Story 1, Scenario 1):
      Given an AI agent with MCP client capability
      When the agent sends MCP initialize request with protocol version "2025-03-26"
      Then the server responds with protocol version "2025-03-26"
      And the server includes serverInfo with name "pytest-mcp" and version number
      And the server indicates capabilities for tools and resources

    This is the highest-level integration test for the initialization workflow.
    Single assertion: The function should return a tuple (not raise NotImplementedError).
    """
    # Act: Call the workflow function we're testing
    result = initialize_server(protocol_version="2025-03-26")

    # Assert: Function should return a tuple of (ProtocolVersion, ServerInfo, ServerCapabilities)
    assert isinstance(result, tuple), (
        "initialize_server should return tuple of validated domain types"
    )


def test_initialize_server_rejects_unsupported_protocol_version_with_structured_error() -> None:
    """Verify initialize_server raises ValueError with ProtocolError details.

    Tests unsupported protocol versions raise structured errors.

    Acceptance Criteria (Story 1, Scenario 2):
      Given an AI agent sending initialize request
      When the agent specifies protocol version "2020-01-01"
      Then the server responds with JSON-RPC error code -32600
      And the error.data includes field "protocolVersion"
      And the error.data includes received_value "2020-01-01"
      And the error.data includes supported_version "2025-03-26"
      And the error.data.detail explains protocol version not supported
          and suggests retry with supported version

    This test verifies the Parse Don't Validate philosophy: validation failures provide
    structured, actionable error information for AI agents to correct and retry.

    Single assertion: ValueError exception contains ProtocolError with all required fields.

    BUG EXPOSED BY THIS TEST:
    The field_validator raises plain ValueError, but Pydantic wraps it in ValidationError.
    The initialize_server function catches ValidationError and creates ProtocolValidationError,
    but the current implementation doesn't properly extract the ValidationError details.
    This test SHOULD FAIL because error.protocol_error won't have the correct field values.
    """
    # Act & Assert: Unsupported protocol version should raise ProtocolValidationError
    with pytest.raises(ProtocolValidationError) as exc_info:
        initialize_server(protocol_version="2020-01-01")

    # Extract the error and its structured protocol_error details
    error = exc_info.value

    # Assert: Verify structured ProtocolError contains all required fields with correct values
    assert error.protocol_error.field == "protocolVersion", (
        "ProtocolError.field should be 'protocolVersion' "
        "to indicate which parameter failed validation"
    )
    assert error.protocol_error.received_value == "2020-01-01", (
        "ProtocolError.received_value should match the unsupported version that was sent"
    )
    assert error.protocol_error.supported_version == "2025-03-26", (
        "ProtocolError.supported_version should indicate which version the server supports"
    )
    assert "Protocol version not supported" in error.protocol_error.detail, (
        "ProtocolError.detail should contain actionable message explaining how to correct the error"
    )
