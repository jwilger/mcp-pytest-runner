"""Domain types for pytest-mcp server.

This module defines workflow functions and minimal nominal types following
the Parse Don't Validate philosophy. Types make illegal states unrepresentable
at the domain boundary.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class ProtocolError(BaseModel):
    """Validation error details for unsupported protocol versions.

    Follows STYLE_GUIDE.md validation error pattern (lines 628-669).
    Provides actionable information for AI agents to correct and retry.
    """

    field: str = Field(description="Parameter name that failed validation")
    received_value: str = Field(description="Value that failed validation")
    supported_version: str = Field(description="Version the server supports")
    detail: str = Field(description="Actionable message for correction")

    model_config = {"frozen": True}


class ProtocolValidationError(ValueError):
    """ValueError subclass carrying structured ProtocolError details.

    Enables Parse Don't Validate philosophy: validation failures provide
    actionable, structured error information for AI agents to correct and retry.

    Follows STYLE_GUIDE.md validation error pattern by attaching field-level
    validation details to exceptions.
    """

    def __init__(self, protocol_error: ProtocolError) -> None:
        """Create validation error with structured protocol error details.

        Args:
            protocol_error: Structured error with field, value, and correction guidance
        """
        self.protocol_error = protocol_error
        super().__init__(protocol_error.detail)


class ProtocolVersion(BaseModel):
    """MCP protocol version identifier.

    Validates protocol version using Pydantic field_validator per ADR-005.
    Parse Don't Validate: Only valid protocol versions can be constructed.
    """

    value: str = Field(description="Protocol version in YYYY-MM-DD format")

    @field_validator("value")
    @classmethod
    def validate_supported_version(cls, v: str) -> str:
        """Validate protocol version against supported version.

        Raises:
            ValueError: When protocol version is not supported
        """
        supported = "2025-03-26"
        if v != supported:
            raise ValueError(
                f"Protocol version {v} not supported. "
                f"Please retry initialization with supported version {supported}."
            )
        return v

    model_config = {"frozen": True}


class ServerInfo(BaseModel):
    """Server metadata included in initialization response.

    Contains server name and version number for AI agent compatibility checking.
    """

    name: str = Field(description="Server name identifier")
    version: str = Field(description="Server version number")

    model_config = {"frozen": True}


class ServerCapabilities(BaseModel):
    """Capabilities advertised by the server during initialization.

    Indicates which MCP features are available (tools, resources, prompts, etc.).
    """

    tools: bool = Field(default=True, description="Server supports tool invocation")
    resources: bool = Field(default=True, description="Server supports resource access")

    model_config = {"frozen": True}


# Story 2: MCP Tool Discovery Domain Types


class Tool(BaseModel):
    """MCP tool definition with name, description, and JSON Schema.

    Represents a discoverable MCP tool with its parameter schema.
    Parse Don't Validate: Only valid tool definitions can be constructed.

    Follows STYLE_GUIDE.md tool discovery pattern.
    """

    name: str = Field(description="Tool name identifier")
    description: str = Field(description="Tool purpose description")
    inputSchema: dict[str, Any] = Field(  # noqa: N815 (MCP spec requires camelCase)
        description="JSON Schema for parameters"
    )

    model_config = {"frozen": True}


class ExecuteTestsParams(BaseModel):
    """Parameters for execute_tests MCP tool.

    Validates pytest execution parameters with security constraints.
    Parse Don't Validate: Only valid parameter combinations can be constructed.

    Follows STYLE_GUIDE.md tool specification (lines 364-417).
    """

    node_ids: list[str] = Field(
        default=[],
        description=(
            "Array of strings. Specific test node IDs to execute. "
            "Example: ['tests/test_user.py::test_login', 'tests/test_auth.py']"
        ),
    )
    markers: str | None = Field(
        default=None,
        description="Pytest marker expression for filtering (e.g., 'not slow and integration')",
    )
    keywords: str | None = Field(
        default=None,
        description="Keyword expression for test name matching (e.g., 'test_user')",
    )
    verbosity: int | None = Field(
        default=None,
        description=(
            "Integer from -2 to 2. Output verbosity level: -2 (quietest) to 2 (most verbose). "
            "Example: 1 for verbose output"
        ),
        ge=-2,
        le=2,
    )
    failfast: bool | None = Field(
        default=None,
        description=(
            "Boolean. Stop execution on first failure. "
            "Example: true to stop immediately, false to continue"
        ),
    )
    maxfail: int | None = Field(
        default=None,
        description="Stop execution after N failures",
        ge=1,
    )
    show_capture: bool | None = Field(
        default=None,
        description="Include captured stdout/stderr in test output",
    )
    timeout: int | None = Field(
        default=None,
        description="Execution timeout in seconds",
        ge=1,
    )

    @model_validator(mode="after")
    def validate_failfast_maxfail_exclusive(self) -> "ExecuteTestsParams":
        """Validate that failfast and maxfail are mutually exclusive.

        Raises:
            ValueError: When both failfast and maxfail are specified
        """
        if self.failfast is not None and self.maxfail is not None:
            raise ValueError(
                "Parameters 'failfast' and 'maxfail' are mutually exclusive. "
                "Specify only one to control test execution stopping behavior."
            )
        return self

    model_config = {"frozen": True, "extra": "forbid"}


class DiscoverTestsParams(BaseModel):
    """Parameters for discover_tests MCP tool.

    Validates test discovery parameters with path traversal protection.
    Parse Don't Validate: Only safe path specifications can be constructed.

    Follows STYLE_GUIDE.md tool specification (lines 442-485).
    """

    path: str | None = Field(
        default=None,
        description="Directory or file path to discover tests within (default: project root)",
    )
    pattern: str | None = Field(
        default=None,
        description="Test file pattern (default: 'test_*.py' or '*_test.py')",
    )

    @field_validator("path")
    @classmethod
    def validate_no_path_traversal(cls, v: str | None) -> str | None:
        """Validate path does not contain directory traversal sequences.

        Security constraint: Prevent path traversal attacks via '..' sequences.

        Raises:
            ValueError: When path contains '..' directory traversal
        """
        if v is None:
            return v

        # Check for directory traversal attempts
        if ".." in Path(v).parts:
            raise ValueError(
                f"Path traversal not allowed: '{v}' contains '..' sequences. "
                "Specify paths within the project boundary only."
            )
        return v

    model_config = {"frozen": True, "extra": "forbid"}


# Story 3: Test Discovery Response Domain Types


class DiscoveredTest(BaseModel):
    """Individual test item discovered by pytest collection.

    Represents a single test with hierarchical organization (module, class, function)
    and source location information. Parse Don't Validate: Only valid test items
    can be constructed.

    Follows STYLE_GUIDE.md successful test discovery pattern (lines 671-720).
    """

    node_id: str = Field(
        description=(
            "pytest node identifier for execution targeting "
            "(e.g., 'tests/test_user.py::TestUserAuth::test_login')"
        )
    )
    module: str = Field(description="Python module path (e.g., 'tests.test_user')")
    class_: str | None = Field(
        default=None,
        alias="class",
        description="Test class name (null for function-based tests)",
    )
    function: str = Field(description="Test function name")
    file: str = Field(description="Source file path")
    line: int | None = Field(
        default=None,
        description="Line number in source file (null when not available from pytest output)",
        ge=1,
    )

    model_config = {"frozen": True, "populate_by_name": True}


class CollectionError(BaseModel):
    """Collection error encountered during test discovery.

    Structured error object providing actionable diagnostic information for
    AI agents to autonomously fix collection failures (syntax errors, import
    failures, etc.). Parse Don't Validate: Only valid error objects can be
    constructed.

    Follows STYLE_GUIDE.md collection error pattern (lines 721-803).
    """

    file: str = Field(description="Source file path where collection error occurred")
    error_type: str = Field(
        description="Error classification (SyntaxError, ImportError, CollectionError, etc.)"
    )
    message: str = Field(description="Human-readable error description")
    line: int | None = Field(
        default=None, description="Line number where error occurred (null if not available)"
    )
    traceback: str | None = Field(
        default=None,
        description="Full traceback text for diagnostic purposes (null if not available)",
    )

    model_config = {"frozen": True}


class DiscoverTestsResponse(BaseModel):
    """Response structure for test discovery operation.

    Contains discovered tests, total count, and collection errors. Parse Don't
    Validate: Response succeeds even with collection errors, enabling AI agents
    to process partial results and autonomously fix issues.

    Follows STYLE_GUIDE.md test discovery response patterns (lines 671-803).
    """

    tests: list[DiscoveredTest] = Field(
        description="Array of discovered test items with hierarchical organization"
    )
    count: int = Field(
        description="Total tests discovered (reflects only successfully discovered tests)", ge=0
    )
    collection_errors: list[CollectionError] = Field(
        default_factory=list,
        description="Collection warnings/errors (empty when discovery succeeds cleanly)",
    )

    @model_validator(mode="after")
    def validate_count_matches_tests(self) -> "DiscoverTestsResponse":
        """Validate that count field matches length of tests array.

        Ensures count accuracy per STYLE_GUIDE.md requirement that count
        reflects usable tests (excludes files with collection errors).

        Raises:
            ValueError: When count does not match tests array length
        """
        if self.count != len(self.tests):
            raise ValueError(
                f"Count mismatch: count field ({self.count}) "
                f"must match tests array length ({len(self.tests)}). "
                "Count reflects only successfully discovered tests."
            )
        return self

    model_config = {"frozen": True}


# Story 4: Test Execution Response Domain Types


class TestResult(BaseModel):
    """Individual test result from pytest execution.

    Represents a single test outcome with timing and diagnostic information.
    Parse Don't Validate: Only valid test outcomes can be constructed.

    Follows STYLE_GUIDE.md successful test execution pattern (lines 518-530).
    """

    node_id: str = Field(
        description="pytest node identifier (e.g., 'tests/test_user.py::test_login')"
    )
    outcome: str = Field(description="Test outcome: 'passed', 'failed', 'skipped', or 'error'")
    duration: float | None = Field(
        default=None,
        description="Test execution time in seconds (None when only summary available)",
        ge=0.0,
    )
    message: str | None = Field(
        default=None, description="Error message for failed/error tests (null for passed/skipped)"
    )
    traceback: str | None = Field(
        default=None, description="Full traceback for failed/error tests (null for passed/skipped)"
    )

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        """Validate test outcome is one of the allowed values.

        Raises:
            ValueError: When outcome is not a valid pytest outcome
        """
        valid_outcomes = {"passed", "failed", "skipped", "error"}
        if v not in valid_outcomes:
            raise ValueError(
                f"Invalid test outcome: '{v}'. Must be one of: {', '.join(sorted(valid_outcomes))}"
            )
        return v

    model_config = {"frozen": True}


class ExecutionSummary(BaseModel):
    """Aggregated test execution statistics.

    Provides summary counts and total duration for test run analysis.
    Parse Don't Validate: Only valid summary statistics can be constructed.

    Follows STYLE_GUIDE.md summary structure (lines 510-516).
    """

    total: int = Field(description="Total number of tests executed", ge=0)
    passed: int = Field(description="Number of tests that passed", ge=0)
    failed: int = Field(description="Number of tests that failed", ge=0)
    skipped: int = Field(description="Number of tests skipped", ge=0)
    errors: int = Field(description="Number of tests with errors", ge=0)
    duration: float = Field(description="Total execution time in seconds", ge=0.0)

    @model_validator(mode="after")
    def validate_totals(self) -> "ExecutionSummary":
        """Validate that component counts sum to total.

        Raises:
            ValueError: When passed + failed + skipped + errors != total
        """
        sum_components = self.passed + self.failed + self.skipped + self.errors
        if sum_components != self.total:
            raise ValueError(
                f"Summary count mismatch: total ({self.total}) must equal "
                f"passed ({self.passed}) + failed ({self.failed}) + "
                f"skipped ({self.skipped}) + errors ({self.errors}) = {sum_components}"
            )
        return self

    model_config = {"frozen": True}


class ExecuteTestsResponse(BaseModel):
    """Response structure for test execution operation.

    Contains execution results, summary statistics, and output. Parse Don't
    Validate: Response structure validated at construction time.

    Follows STYLE_GUIDE.md test execution response pattern (lines 500-570).
    """

    exit_code: int = Field(
        description="pytest exit code: 0 (all passed), 1 (some failed), 5 (no tests collected)"
    )
    summary: ExecutionSummary = Field(description="Aggregated test execution statistics")
    tests: list[TestResult] = Field(description="Individual test results with outcomes")
    text_output: str = Field(description="pytest's native text output (preserves formatting)")

    @field_validator("exit_code")
    @classmethod
    def validate_exit_code(cls, v: int) -> int:
        """Validate exit code is a success/failure code (not error code).

        Raises:
            ValueError: When exit code indicates execution error (2, 3, 4)
        """
        valid_codes = {0, 1, 5}
        if v not in valid_codes:
            raise ValueError(
                f"Invalid exit code for success response: {v}. "
                f"Use ExecutionError for exit codes 2, 3, 4, or timeout. "
                f"Valid success codes: {sorted(valid_codes)}"
            )
        return v

    @model_validator(mode="after")
    def validate_count_matches_tests(self) -> "ExecuteTestsResponse":
        """Validate that summary.total matches length of tests array.

        Ensures count accuracy per STYLE_GUIDE.md requirement.

        Raises:
            ValueError: When summary.total does not match tests array length
        """
        if self.summary.total != len(self.tests):
            raise ValueError(
                f"Count mismatch: summary.total ({self.summary.total}) "
                f"must match tests array length ({len(self.tests)})"
            )
        return self

    model_config = {"frozen": True}


class ExecutionError(BaseModel):
    """Error details for failed test execution (exit codes 2-4 or timeout).

    Provides diagnostic information for execution failures that prevent
    pytest from completing normally. Parse Don't Validate: Only valid
    execution errors can be constructed.

    Follows STYLE_GUIDE.md execution failure pattern (lines 572-627).
    """

    exit_code: int = Field(
        description=(
            "pytest exit code: 2 (interrupted), 3 (internal error), "
            "4 (usage error), or -1 (timeout)"
        )
    )
    stdout: str = Field(description="Captured standard output")
    stderr: str = Field(description="Captured standard error (contains diagnostic info)")
    timeout_exceeded: bool = Field(description="Whether timeout caused the failure")
    command: list[str] = Field(
        description="Exact command executed (for reproduction)", min_length=1
    )
    duration: float = Field(description="Time spent before failure in seconds", ge=0.0)

    @field_validator("exit_code")
    @classmethod
    def validate_exit_code(cls, v: int) -> int:
        """Validate exit code is an error code (not success code).

        Raises:
            ValueError: When exit code indicates success (0, 1, 5)
        """
        error_codes = {-1, 2, 3, 4}
        if v not in error_codes:
            raise ValueError(
                f"Invalid exit code for error response: {v}. "
                f"Use ExecuteTestsResponse for exit codes 0, 1, 5. "
                f"Valid error codes: {sorted(error_codes)}"
            )
        return v

    model_config = {"frozen": True}


# Workflow function signatures
# Implementation deferred to TDD phase (N.7)


def list_tools() -> list[Tool]:
    """List all available MCP tools with their parameter schemas.

    Returns tool definitions for pytest execution and discovery capabilities.

    Returns:
        List of Tool definitions with names, descriptions, and JSON schemas
    """
    return [
        Tool(
            name="execute_tests",
            description="Execute pytest tests with filtering and output options",
            inputSchema=ExecuteTestsParams.model_json_schema(),
        ),
        Tool(
            name="discover_tests",
            description="Discover available tests in the project",
            inputSchema=DiscoverTestsParams.model_json_schema(),
        ),
    ]


def initialize_server(
    protocol_version: str,
) -> tuple[ProtocolVersion, ServerInfo, ServerCapabilities]:
    """Initialize MCP server connection with protocol version validation.

    Parse Don't Validate: Returns validated domain types or raises
    ProtocolValidationError with structured ProtocolError details for
    unsupported protocol versions.

    Args:
        protocol_version: Protocol version string from AI agent

    Returns:
        Tuple of validated protocol version, server info, and capabilities

    Raises:
        ProtocolValidationError: When protocol version is unsupported
            (subclass of ValueError with protocol_error attribute)
    """
    try:
        # Pydantic validation happens here (ADR-005 compliance)
        validated_version = ProtocolVersion(value=protocol_version)
    except ValidationError:
        # Extract validation error and wrap in domain exception
        protocol_error = ProtocolError(
            field="protocolVersion",
            received_value=protocol_version,
            supported_version="2025-03-26",
            detail=(
                "Protocol version not supported. "
                "Please retry initialization with supported version."
            ),
        )
        raise ProtocolValidationError(protocol_error) from None

    server_info = ServerInfo(name="pytest-mcp", version="0.1.0")
    capabilities = ServerCapabilities(tools=True, resources=True)
    return (validated_version, server_info, capabilities)


def discover_tests(
    params: DiscoverTestsParams,
) -> DiscoverTestsResponse:
    """Discover available tests in the project without executing them.

    Parse Don't Validate: Accepts validated DiscoverTestsParams with path
    traversal protection, returns validated DiscoverTestsResponse with
    discovered tests and optional collection errors.

    Args:
        params: Validated discovery parameters with security constraints

    Returns:
        DiscoverTestsResponse with discovered tests, count, and collection errors
    """
    # Build pytest command for test discovery
    # Use -q to get simpler output format
    cmd = ["pytest", "--collect-only", "-q"]
    if params.path:
        cmd.append(params.path)
    if params.pattern:
        cmd.extend(["-o", f"python_files={params.pattern}"])

    # Execute pytest subprocess
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    # Parse pytest output to discover tests
    # pytest --collect-only -q outputs lines like:
    # tests/test_file.py::test_function
    # tests/test_file.py::TestClass::test_method
    tests: list[DiscoveredTest] = []
    collection_errors: list[CollectionError] = []

    # Check stderr for collection errors (minimal implementation)
    if result.stderr.strip():
        # Create basic CollectionError when stderr contains errors
        collection_errors.append(
            CollectionError(
                file=params.path or ".",
                error_type="CollectionError",
                message=result.stderr.strip(),
            )
        )

    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        # Skip empty lines, separator lines, and summary lines
        if not line or line.startswith("=") or "collected" in line.lower():
            continue

        # Look for lines containing "::" which indicate test node IDs
        if "::" in line:
            node_id = line
            parts = node_id.split("::")

            if len(parts) < 2:
                continue

            file_path = parts[0]

            # Extract module from file path (e.g., "tests/test_user.py" -> "tests.test_user")
            module = file_path.replace("/", ".").replace(".py", "")

            # Determine if class-based or function-based test
            if len(parts) == 3:
                # Class-based test: file.py::TestClass::test_method
                class_name = parts[1]
                function_name = parts[2]
            elif len(parts) == 2:
                # Function-based test: file.py::test_function
                class_name = None
                function_name = parts[1]
            else:
                # Skip malformed lines
                continue

            tests.append(
                DiscoveredTest.model_construct(
                    node_id=node_id,
                    module=module,
                    class_=class_name,
                    function=function_name,
                    file=file_path,
                    line=None,  # pytest -q doesn't provide line numbers
                )
            )

    return DiscoverTestsResponse(
        tests=tests,
        count=len(tests),
        collection_errors=collection_errors,
    )


def execute_tests(
    params: ExecuteTestsParams,
) -> ExecuteTestsResponse | ExecutionError:
    """Execute pytest tests with given parameters.

    Parse Don't Validate: Accepts validated ExecuteTestsParams, returns
    validated ExecuteTestsResponse with test results or ExecutionError.

    Args:
        params: Validated test execution parameters

    Returns:
        ExecuteTestsResponse with test results and summary
    """
    # Build pytest command with node_ids (required parameter)
    if params.node_ids:
        cmd = ["pytest", *params.node_ids, "-v"]
    else:
        # When no node_ids specified, pytest will use its default discovery
        cmd = ["pytest", "-v"]

    # Execute pytest with timeout and exception handling
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=params.timeout
            if params.timeout is not None
            else 30,  # Use param or default to 30
        )
    except subprocess.TimeoutExpired as e:
        # Return ExecutionError for timeout
        # stdout/stderr are str|bytes|None when text=True; ensure str type
        stdout_str = e.stdout if isinstance(e.stdout, str) else ""
        stderr_str = e.stderr if isinstance(e.stderr, str) else ""
        return ExecutionError(
            exit_code=-1,
            stdout=stdout_str,
            stderr=stderr_str,
            timeout_exceeded=True,
            command=cmd,
            duration=30.0,
        )
    except FileNotFoundError:
        # Return ExecutionError when pytest not found
        return ExecutionError(
            exit_code=-1,
            stdout="",
            stderr="pytest command not found",
            timeout_exceeded=False,
            command=cmd,
            duration=0.0,
        )

    # Parse summary line for test counts and duration
    # Example: "====== 2 passed in 0.01s ======="
    # Example: "====== 1 failed in 0.02s ======="
    # NOTE: Primitive string parsing is intentional for Round 2 (minimal implementation)
    # Future rounds will strengthen with JSON output (--json-report) or structured parsing
    passed_count = 0
    failed_count = 0
    duration = 0.0

    summary_match = re.search(r"(\d+) passed(?:, \d+ warnings?)? in ([\d.]+)s", result.stdout)
    if summary_match:
        passed_count = int(summary_match.group(1))
        duration = float(summary_match.group(2))

    failed_match = re.search(r"(\d+) failed", result.stdout)
    if failed_match:
        failed_count = int(failed_match.group(1))
        # Extract duration from failed summary if passed summary not found
        if duration == 0.0:
            failed_duration_match = re.search(r"(\d+) failed in ([\d.]+)s", result.stdout)
            if failed_duration_match:
                duration = float(failed_duration_match.group(2))

    # Check for execution errors (exit codes 2-4)
    if result.returncode in {2, 3, 4}:
        return ExecutionError(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout_exceeded=False,
            command=cmd,
            duration=duration,
        )

    # Parse individual test results from verbose output
    # Example line: "tests/fixtures/sample_tests/test_sample.py::test_passing PASSED"
    # Example line: "tests/fixtures/sample_tests/test_sample.py::test_failing FAILED"
    tests = []
    for line in result.stdout.split("\n"):
        if "::test_" in line and " PASSED" in line and not line.startswith("PASSED"):
            # Extract node_id (everything before " PASSED")
            node_id = line.split(" PASSED")[0].strip()
            tests.append(
                TestResult(
                    node_id=node_id,
                    outcome="passed",
                    duration=None,  # Individual durations not available in Round 2
                )
            )
        elif "::test_" in line and " FAILED" in line and not line.startswith("FAILED"):
            # Extract node_id (everything before " FAILED")
            node_id = line.split(" FAILED")[0].strip()
            tests.append(
                TestResult(
                    node_id=node_id,
                    outcome="failed",
                    duration=None,
                    message="Test failed",  # Minimal message for Round 4
                )
            )

    # Return minimal valid response
    return ExecuteTestsResponse(
        exit_code=result.returncode,
        summary=ExecutionSummary(
            total=passed_count + failed_count,
            passed=passed_count,
            failed=failed_count,
            skipped=0,
            errors=0,
            duration=duration,
        ),
        tests=tests,
        text_output=result.stdout,
    )
