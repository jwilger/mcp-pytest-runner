"""Tests for test execution with parameter support (Story 4).

Outside-In TDD: Start with highest-level acceptance test for test execution.
Test the workflow function directly before drilling down to components.
"""

from pytest_mcp.domain import ExecuteTestsParams, ExecuteTestsResponse, execute_tests


def test_execute_tests_with_no_parameters_returns_execution_response() -> None:
    """Verify execute_tests returns ExecuteTestsResponse for all tests.

    Acceptance Criteria (Story 4, Scenario 1):
      Given a project with passing pytest tests
      When the agent calls execute_tests for fixture tests
      Then the server executes pytest for specified tests
      And the response includes exit_code 0
      And summary shows all tests passed with total count and duration
      And tests array includes minimal details for each passing test

    This is the highest-level integration test for the test execution workflow.
    Single assertion: The function should return an ExecuteTestsResponse object.
    """
    # Act: Call the workflow function targeting fixture tests
    params = ExecuteTestsParams(node_ids=["tests/fixtures/sample_tests/"])
    result = execute_tests(params)

    # Assert: Function should return ExecuteTestsResponse object
    assert isinstance(result, ExecuteTestsResponse), (
        "execute_tests should return an ExecuteTestsResponse object"
    )


def test_execute_tests_summary_total_reflects_actual_test_count() -> None:
    """Verify summary.total matches actual number of tests executed.

    Acceptance Criteria (Story 4, Scenario 1):
      Given a project with pytest tests (both passing and failing)
      When the agent calls execute_tests for fixture tests
      Then summary shows total count matching all tests executed

    TDD Round 2: Verify summary contains accurate test count from pytest output.
    The fixture directory tests/fixtures/sample_tests/ contains exactly 4 tests:
      - test_passing (passes)
      - test_another_passing (passes)
      - test_failing (fails)
      - test_slow_execution (passes)

    Single assertion: summary.total should equal 4 (the actual test count).
    """
    # Arrange: Create parameters for executing fixture tests
    params = ExecuteTestsParams(node_ids=["tests/fixtures/sample_tests/"])

    # Act: Execute tests
    result = execute_tests(params)

    # Assert: Result is success response (not error)
    assert isinstance(result, ExecuteTestsResponse)

    # Assert: Summary total should match all 4 fixture tests
    assert result.summary.total == 4, (
        f"Expected summary.total to be 4 (matching fixture test count), "
        f"but got {result.summary.total}"
    )

    # Assert: Summary should reflect 3 passed, 1 failed
    assert result.summary.passed == 3, (
        f"Expected summary.passed to be 3, but got {result.summary.passed}"
    )
    assert result.summary.failed == 1, (
        f"Expected summary.failed to be 1, but got {result.summary.failed}"
    )


def test_execute_tests_filters_by_node_ids() -> None:
    """Verify node_ids parameter filters which tests execute.

    Acceptance Criteria (Story 4, Scenario 2):
      Given a project with multiple pytest tests
      When the agent calls execute_tests with specific node_ids
      Then only the specified tests execute
      And summary.total reflects only the filtered test count

    TDD Round 3: Verify execute_tests respects node_ids parameter filtering.
    The fixture directory tests/fixtures/sample_tests/ contains exactly 2 tests:
      - test_passing
      - test_another_passing

    When node_ids specifies only test_passing, exactly 1 test should execute.

    Single assertion: summary.total should equal 1 (only the specified test).
    """
    # Arrange: Create parameters targeting only one specific test
    params = ExecuteTestsParams(
        node_ids=["tests/fixtures/sample_tests/test_sample.py::test_passing"]
    )

    # Act: Execute tests with node_ids filter
    result = execute_tests(params)

    # Assert: Result is success response (not error)
    assert isinstance(result, ExecuteTestsResponse)

    # Assert: Summary total should be 1 (only the specified test executed)
    assert result.summary.total == 1, (
        f"Expected summary.total to be 1 when filtering by node_ids=['test_passing'], "
        f"but got {result.summary.total}. "
        "The execute_tests implementation should pass node_ids to pytest command "
        "instead of executing all tests in the hardcoded directory."
    )


def test_execute_tests_captures_failed_test_details() -> None:
    """Verify failed tests include traceback and message.

    Acceptance Criteria (Story 4, Scenario 2):
      Given a project with a failing pytest test
      When the agent calls execute_tests for that specific failing test
      Then the response includes exit_code 1
      And summary shows failed count
      And tests array includes traceback and message for the failed test

    TDD Round 4: Verify execute_tests captures failure details for AI agents.
    This is CRITICAL for the core TDD use case - AI agents need failure information
    to understand what went wrong and how to fix it.

    The fixture test_failing intentionally fails with assertion error.

    Single assertion: Failed test should have a non-None message field.
    """
    # Arrange: Create parameters targeting the specific failing test
    params = ExecuteTestsParams(
        node_ids=["tests/fixtures/sample_tests/test_sample.py::test_failing"]
    )

    # Act: Execute the failing test
    result = execute_tests(params)

    # Assert: Result is success response (not error - pytest ran successfully)
    assert isinstance(result, ExecuteTestsResponse), (
        "execute_tests should return ExecuteTestsResponse even when tests fail"
    )

    # Assert: Exit code should be 1 (pytest exit code for test failures)
    assert result.exit_code == 1, (
        f"Expected exit_code 1 for failed test, but got {result.exit_code}"
    )

    # Assert: Summary should reflect the failure
    assert result.summary.failed == 1, (
        f"Expected summary.failed to be 1, but got {result.summary.failed}"
    )

    # Assert: Should have exactly one test in results array
    assert len(result.tests) == 1, f"Expected 1 test in results, but got {len(result.tests)}"

    # Assert: Failed test should have error message (MAIN ASSERTION)
    failed_test = result.tests[0]
    assert failed_test.outcome == "failed", (
        f"Expected outcome 'failed', but got '{failed_test.outcome}'"
    )
    assert failed_test.message is not None, (
        "Failed test should have error message for AI agent debugging. "
        f"Test: {failed_test.node_id}, Message: {failed_test.message}"
    )


def test_execute_tests_summary_total_matches_tests_array_length() -> None:
    """Verify summary.total equals len(tests) when discovering all tests.

    Bug Discovery (Story 11):
      Given a project with multiple pytest tests
      When the agent calls execute_tests with no parameters (discovers all tests)
      Then summary.total must equal the length of the tests array
      And this catches the bug where summary parsing and test result parsing diverge

    Root Cause:
      - summary.total calculated from regex parsing of summary line (line 793)
      - tests array populated from regex parsing of verbose output (line 800)
      - If summary parsing fails/differs, counts will mismatch
      - ExecuteTestsResponse validator (line 457) requires summary.total == len(tests)

    Single assertion: summary.total must equal len(response.tests).
    """
    # Arrange: Create parameters with specific test to verify summary matching logic
    params = ExecuteTestsParams(
        node_ids=[
            "tests/test_tool_discovery.py::test_list_tools_returns_array_with_two_tool_definitions"
        ],
        timeout=30,
    )

    # Act: Execute all tests
    result = execute_tests(params)

    # Assert: Result is success response (not error - pytest ran successfully)
    assert isinstance(result, ExecuteTestsResponse), (
        "execute_tests should return ExecuteTestsResponse"
    )

    # Assert: summary.total must match tests array length (MAIN ASSERTION)
    assert result.summary.total == len(result.tests), (
        f"Bug detected: summary.total ({result.summary.total}) does not match "
        f"tests array length ({len(result.tests)}). This indicates summary parsing "
        f"and test result parsing are producing different counts. "
        f"Summary parsing extracts from summary line, test parsing extracts from verbose output."
    )


def test_execute_tests_respects_timeout_parameter() -> None:
    """Verify execute_tests respects params.timeout value.

    Acceptance Criteria:
      Given a test that takes longer than the specified timeout
      When the agent calls execute_tests with a short timeout (e.g., timeout=1)
      Then the function returns an ExecutionError
      And timeout_exceeded is True

    Current Implementation Bug:
      Line 702 in domain.py hardcodes timeout=30 instead of using params.timeout
      This test will fail until the implementation uses params.timeout

    Single assertion: Result should be ExecutionError with timeout_exceeded=True.
    """
    # Arrange: Create parameters with very short timeout for slow test
    params = ExecuteTestsParams(
        node_ids=["tests/fixtures/sample_tests/test_slow.py::test_slow_execution"],
        timeout=1,  # 1 second timeout, but test takes 5 seconds
    )

    # Act: Execute slow test with short timeout
    result = execute_tests(params)

    # Assert: Should return ExecutionError with timeout_exceeded=True (MAIN ASSERTION)
    from pytest_mcp.domain import ExecutionError

    assert isinstance(result, ExecutionError) and result.timeout_exceeded is True, (
        f"Expected ExecutionError with timeout_exceeded=True when test exceeds timeout, "
        f"but got {type(result).__name__}. "
        "The implementation should use params.timeout instead of hardcoded 30 seconds."
    )


def test_execute_tests_parses_summary_with_warnings() -> None:
    r"""Verify execute_tests correctly parses summary lines with warnings.

    Bug Discovery:
      Given a project where pytest outputs warnings
      When the agent calls execute_tests with no parameters (runs all tests)
      Then the summary line format changes from "N passed in X.XXs"
      To "N passed, M warning in X.XXs"
      And the current regex r"(\d+) passed in ([\d.]+)s" fails to match
      And this causes summary.total to be 0 instead of the actual test count

    Current Implementation Bug:
      Line 737 in domain.py uses regex: r"(\d+) passed in ([\d.]+)s"
      This regex doesn't account for the optional ", N warning" clause
      When warnings are present, regex fails to match, passed_count remains 0
      This causes validation error: summary.total (0) != len(tests) (actual count)

    Fix Required:
      Update regex to: r"(\d+) passed(?:, \d+ warnings?)? in ([\d.]+)s"
      This makes the warning clause optional with non-capturing group (?:...)

    Single assertion: summary.total should be > 0 when tests execute with warnings.
    """
    # Arrange: Create parameters with empty node_ids list (discovers and runs all tests)
    # Running all tests produces warnings, demonstrating the bug
    params = ExecuteTestsParams(node_ids=["tests/test_main.py"], timeout=60)

    # Act: Execute all discovered tests (pytest will output warnings)
    result = execute_tests(params)

    # Assert: Result should be ExecuteTestsResponse (not validation error)
    assert isinstance(result, ExecuteTestsResponse), (
        f"execute_tests should return ExecuteTestsResponse even with warnings, "
        f"but got {type(result).__name__}"
    )

    # Assert: summary.total should be greater than 0 (MAIN ASSERTION)
    # If regex fails to parse warnings format, summary.total will be 0
    assert result.summary.total > 0, (
        f"Expected summary.total > 0 when parsing pytest output with warnings, "
        f"but got {result.summary.total}. "
        "This indicates the summary line regex failed to match the format "
        '"N passed, M warning in X.XXs". '
        "The regex should be updated to handle optional warning clause."
    )

    # Assert: summary.passed should also be greater than 0
    assert result.summary.passed > 0, (
        f"Expected summary.passed > 0 when tests pass with warnings, "
        f"but got {result.summary.passed}"
    )
