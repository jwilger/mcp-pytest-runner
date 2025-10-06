# Requirements Analysis: pytest-mcp

**Document Version:** 1.0
**Date:** October 3, 2025 (Friday)
**Project:** pytest-mcp
**Phase:** 1 - Requirements Analysis

## Executive Summary

pytest-mcp provides an opinionated MCP (Model Context Protocol) server interface for pytest test execution, enabling AI agents to run tests consistently and safely without requiring arbitrary shell command access. This standardizes how AI assistants interact with pytest, replacing ad-hoc shell invocations with a structured, predictable protocol.

**Business Value**: Enables reliable AI-assisted TDD workflows by ensuring test execution behaves consistently across all AI interactions. Improves security by eliminating the need for broad shell access permissions when AI agents need to run tests. Reduces developer friction when using AI assistants during testing and debugging.

## Current State Analysis

**Problem**: AI assistants often run pytest in inconsistent ways when using generic shell execution tools (Bash tool, arbitrary command execution). This creates unpredictable behavior and requires users to grant broad shell access to AI agents, introducing security concerns.

**Pain Points**:
- AI agents execute pytest with varying command patterns and argument combinations
- Inconsistent test execution leads to unreliable TDD workflows and confusing results
- Generic shell access allows AI agents arbitrary command execution beyond test running
- No standardized interface constrains AI behavior to safe, predictable test operations
- Users must choose between enabling broad shell access or blocking AI from running tests entirely

**Opportunity**: MCP servers enable tools to expose functionality through structured, opinionated interfaces. A pytest-specific MCP server provides a consistent, safe way for AI agents to execute tests without requiring arbitrary shell command access.

## Functional Requirements

### FR-1: Pytest Execution Integration
**Why**: Provides a standardized, opinionated interface for AI agents to execute pytest consistently, eliminating the variability and security concerns of arbitrary shell command execution.

**FR-1.1 Complete CLI Argument Support**
- System provides access to all pytest command-line arguments and options through structured MCP tool parameters
- Supports filtering (markers, keywords, node IDs), output control (verbosity, reporting), and execution options (parallel, failfast)
- **Value**: Preserves full pytest capabilities while constraining execution to predictable, validated patterns

**FR-1.2 Test Discovery**
- System exposes pytest's test collection mechanism through structured MCP interface
- Discovers test structure without execution
- **Value**: AI agents access test organization through consistent interface rather than parsing shell command output

**FR-1.3 Result Reporting**
- System captures and structures pytest output including pass/fail status, error messages, stack traces, and execution timing through consistent MCP response format
- **Value**: AI agents receive predictable, parseable test results instead of fragile shell output parsing

**FR-1.4 Exit Code Semantics**
- System preserves pytest's standard exit codes (0=success, 1=failures, 2=interrupted, etc.)
- **Value**: Supports automation and CI/CD integration patterns

### FR-2: Distribution and Installation
**Why**: Minimizes installation friction; users must access the tool without complex setup procedures.

**FR-2.1 uvx Compatibility**
- System installable and executable via `uvx pytest-mcp`
- Supports ephemeral execution without persistent installation
- **Value**: Zero-configuration usage for developers already using uv toolchain

**FR-2.2 PyPI Publishing**
- Package discoverable and installable from PyPI
- Follows Python packaging standards for metadata, versioning, and dependencies
- **Value**: Standard distribution mechanism familiar to Python developers

**FR-2.3 Semantic Versioning**
- System follows semver for version numbering
- Breaking changes increment major version
- **Value**: Dependency management compatibility and upgrade safety

### FR-3: Development Environment
**Why**: Ensures consistent, reproducible development across contributors and environments.

**FR-3.1 Nix Flake Integration**
- Development environment defined via flake.nix
- Includes Python toolchain, dependencies, and development tools
- **Value**: Eliminates "works on my machine" issues; reproducible builds

**FR-3.2 Development Tooling**
- Environment includes formatters, linters, type checkers, and test runners
- **Value**: Enforces code quality standards automatically

### FR-4: Continuous Integration and Deployment
**Why**: Automates quality validation and release processes; reduces human error in publishing.

**FR-4.1 CI Quality Gates**
- GitHub Actions workflow validates tests, type checking, linting, and security scanning
- Blocks merges on quality gate failures
- **Value**: Maintains code quality without manual review burden

**FR-4.2 Automated PyPI Publishing**
- GitHub Actions workflow publishes releases to PyPI on tag creation
- Handles authentication, version validation, and distribution upload
- **Value**: Eliminates manual publishing errors; accelerates release cycles

**FR-4.3 Release Workflow**
- System enforces semantic versioning for releases
- Generates release notes from commits or changelog
- **Value**: Consistent release process; clear version history

## Non-Functional Requirements

### NFR-1: Code Quality Standards
**Why**: High-quality codebase reduces bugs, improves maintainability, and builds user trust.

**NFR-1.1 Type Safety**
- Complete type annotations verified by MyPy strict mode
- Type errors block commits
- **Value**: Prevents entire class of runtime errors; improves IDE support

**NFR-1.2 Code Style**
- RUFF enforces ALL available rules
- Consistent formatting and idiom usage
- **Value**: Readable codebase; reduced review friction

**NFR-1.3 Domain Modeling**
- Pydantic v2 with `ConfigDict(frozen=True, extra='forbid')` for value objects
- Parse-don't-validate philosophy for inputs
- **Value**: Invalid states become unrepresentable; eliminates defensive programming

### NFR-2: Test Coverage and Quality
**Why**: Comprehensive testing validates behavior and prevents regressions.

**NFR-2.1 Line and Branch Coverage**
- Minimum 80% line coverage, 80% branch coverage
- Coverage metrics tracked per commit
- **Value**: High confidence in behavior; reduces production defects

**NFR-2.2 Mutation Testing**
- Minimum 80% mutation score using mutmut
- Validates test suite effectiveness, not just coverage
- **Value**: Tests actually validate behavior, not just execute code paths

**NFR-2.3 Property-Based Testing**
- Hypothesis for domain boundary validation
- Focuses on invariants and edge cases
- **Value**: Discovers unexpected failure modes human testers miss

### NFR-3: Security
**Why**: Prevents vulnerabilities from reaching production; protects users.

**NFR-3.1 Security Scanning**
- Bandit scans for common Python security issues
- Blocks commits on high-severity findings
- **Value**: Early detection of security anti-patterns

**NFR-3.2 Dependency Auditing**
- Regular scans for known vulnerabilities in dependencies
- Automated updates for security patches
- **Value**: Reduces attack surface from third-party code

### NFR-4: Performance Expectations
**Why**: Poor performance creates friction in interactive AI workflows.

**NFR-4.1 Response Latency**
- Test discovery completes in responsive time for typical projects
- Result reporting streams progressively, not blocking on completion
- **Value**: Maintains conversational flow; reduces perceived wait time

**NFR-4.2 Resource Efficiency**
- Server operates with minimal memory overhead when idle
- Scales to projects with thousands of test cases
- **Value**: Usable on developer machines without performance degradation

### NFR-5: Platform Compatibility
**Why**: Supports diverse development environments; maximizes accessibility.

**NFR-5.1 Python Version Support**
- Requires Python 3.12 or later
- Leverages modern language features and performance improvements
- **Value**: Reduces compatibility matrix complexity; uses best available tooling

**NFR-5.2 Operating System Support**
- Compatible with Linux, macOS, and Windows
- Uses cross-platform libraries and avoids OS-specific APIs
- **Value**: Accessible to entire Python developer community

### NFR-6: Cognitive Load Management (TRACE Framework)
**Why**: Maintainable code reduces long-term costs and enables contributor onboarding.

**NFR-6.1 TRACE Quality Gate**
- Overall TRACE score ≥70% required for PR acceptance
- Each dimension (Type-first, Readability, Atomic, Cognitive, Essential) ≥50%
- **Value**: Ensures code remains understandable and maintainable over time

**NFR-6.2 Type-First Thinking**
- Domain types prevent invalid states at compile time
- Leverage Pydantic validation for external boundaries
- **Value**: Bugs caught during development, not in production

**NFR-6.3 Readability Standard**
- New developers understand modules within 30 seconds
- Clear naming, focused responsibilities, minimal abstraction
- **Value**: Reduces onboarding time; improves debugging efficiency

## User Stories (High-Level Overview)

**Note**: Detailed user stories with Gherkin acceptance criteria created in Phase 6 (Story Planning).

### Epic 1: MCP Server Foundation

**Story 1.1: MCP Protocol Implementation**
- **Description**: WHAT: System implements MCP protocol for server discovery and communication
- **Value**: WHY: Provides standardized interface for AI agents to discover pytest capabilities without shell access
- **Acceptance Criteria**:
  - Given MCP client connects to server
  - When client requests server capabilities
  - Then server responds with available tools and resources

**Story 1.2: Pytest Execution Tool**
- **Description**: WHAT: System exposes pytest execution as structured MCP tool with validated parameters
- **Value**: WHY: Replaces inconsistent shell command invocations with predictable, safe test execution interface
- **Acceptance Criteria**:
  - Given AI agent requests test execution via MCP tool
  - When system receives validated pytest arguments
  - Then tests execute consistently and results return in structured format

### Epic 2: Package Distribution

**Story 2.1: PyPI Package Configuration**
- **Description**: WHAT: System configured for PyPI publishing
- **Value**: WHY: Enables installation via standard Python tooling
- **Acceptance Criteria**:
  - Given package metadata properly configured
  - When package built for distribution
  - Then package installable via pip and uvx

**Story 2.2: Automated Release Pipeline**
- **Description**: WHAT: GitHub Actions automate PyPI publishing on releases
- **Value**: WHY: Eliminates manual publishing errors and delays
- **Acceptance Criteria**:
  - Given new version tagged in repository
  - When GitHub Actions workflow executes
  - Then package published to PyPI automatically

### Epic 3: Development Infrastructure

**Story 3.1: Nix Development Environment**
- **Description**: WHAT: Flake.nix defines reproducible development environment
- **Value**: WHY: Consistent tooling across all contributors
- **Acceptance Criteria**:
  - Given developer runs `nix develop`
  - When environment activates
  - Then all development tools available and configured

**Story 3.2: CI Quality Pipeline**
- **Description**: WHAT: GitHub Actions validate code quality on every commit
- **Value**: WHY: Prevents quality regressions from merging
- **Acceptance Criteria**:
  - Given code pushed to branch
  - When CI workflow executes
  - Then tests, types, linting, security, mutation testing all validate

### Epic 4: Core Testing Integration

**Story 4.1: Test Discovery Resource**
- **Description**: WHAT: System exposes pytest test collection as structured MCP resource
- **Value**: WHY: AI agents discover test structure through consistent interface instead of parsing shell output
- **Acceptance Criteria**:
  - Given project with pytest tests
  - When MCP client requests test discovery
  - Then test structure returned with module/class/function hierarchy in predictable format

**Story 4.2: Comprehensive Argument Support**
- **Description**: WHAT: All pytest CLI arguments accessible via validated MCP tool parameters
- **Value**: WHY: Preserves full pytest functionality while constraining AI agents to safe, predictable execution patterns
- **Acceptance Criteria**:
  - Given AI agent specifies pytest arguments (markers, keywords, verbosity, etc.) via MCP parameters
  - When test execution requested via MCP tool
  - Then pytest runs with validated arguments in consistent manner

### Epic 5: MCP Server Integration

**Story 5.1: MCP Server Runtime Integration**
- **Description**: WHAT: System implements MCP JSON-RPC protocol over stdio, enabling pytest-mcp to function as an actual MCP server that AI agents can connect to
- **Value**: WHY: Bridges the gap between workflow functions (domain.py) and usable MCP server; enables users to actually use pytest-mcp by adding it to Claude Code or other MCP client configurations
- **Acceptance Criteria**:
  - Given pytest-mcp installed via pip or uvx
  - When user launches pytest-mcp server process
  - Then server listens on stdio for MCP JSON-RPC messages
  - And server responds to MCP initialize request with protocol handshake
  - And server advertises execute_tests and discover_tests tools
  - When AI agent calls execute_tests tool via MCP protocol
  - Then server routes request to domain.execute_tests() workflow function
  - And returns structured response via MCP protocol
  - When AI agent calls discover_tests tool via MCP protocol
  - Then server routes request to domain.discover_tests() workflow function
  - And returns structured response via MCP protocol

**Story 5.2: Server Entry Point Configuration**
- **Description**: WHAT: Package includes executable entry point that users can invoke as `pytest-mcp` command
- **Value**: WHY: Enables users to add pytest-mcp to MCP client configurations (like Claude Code) by referencing the entry point command
- **Acceptance Criteria**:
  - Given pytest-mcp installed via pip
  - When user runs `pytest-mcp` command
  - Then MCP server process starts and listens on stdio
  - Given pytest-mcp PyPI package
  - When examining package metadata
  - Then pyproject.toml includes [project.scripts] entry point
  - And entry point maps pytest-mcp command to main() function

**Story 5.3: MCP Client Configuration Compatibility**
- **Description**: WHAT: Server configuration instructions enable users to add pytest-mcp to MCP clients like Claude Code
- **Value**: WHY: Users can actually use pytest-mcp in their AI development workflows, not just as standalone workflow functions
- **Acceptance Criteria**:
  - Given pytest-mcp installed and configured
  - When user adds pytest-mcp to Claude Code MCP server configuration
  - Then Claude Code successfully connects to pytest-mcp server
  - And pytest-mcp tools appear in Claude Code's available tools
  - When Claude requests execute_tests via MCP protocol
  - Then pytest executes and results return to Claude
  - And Claude can interpret and act on structured test results

## Success Criteria

**User Adoption Metrics**:
- Developers reduce test debugging time through AI integration
- PyPI download growth indicates community adoption
- GitHub stars and forks demonstrate interest and contribution

**Quality Metrics**:
- Zero high-severity security vulnerabilities
- ≥80% mutation score maintained across releases
- ≥70% TRACE score for all modules
- CI pipeline passes on 100% of main branch commits

**Functional Success**:
- AI agents execute tests consistently through MCP interface without shell access requirements
- Users install and run via `uvx pytest-mcp` without configuration
- Automated releases publish to PyPI without manual intervention
- AI-assisted TDD workflows operate reliably with predictable test execution behavior

## Dependencies and Constraints

### Technical Dependencies
- **Python 3.12+**: Required for modern language features and performance
- **pytest**: Core dependency; version compatibility must be maintained
- **Pydantic v2**: Domain modeling foundation
- **MCP SDK**: Protocol implementation library (Python MCP SDK)
- **uv/uvx**: Distribution mechanism for ephemeral execution

### Licensing Constraint
- **MIT License**: Permissive open-source license enabling broad adoption and commercial use

### Distribution Constraints
- **PyPI Standards**: Package must comply with PEP standards for metadata, structure, and dependencies
- **Semantic Versioning**: Version numbering must follow semver specification

### Development Constraints
- **Nix Flake**: Development environment managed via Nix for reproducibility
- **GitHub Actions**: CI/CD must run on GitHub-hosted runners (no external infrastructure)

## Risk Assessment

### Technical Risks

**Risk: MCP Protocol Evolution**
- **Impact**: Breaking changes in MCP specification require rapid adaptation
- **Mitigation**: Pin MCP SDK versions; monitor specification changes; maintain compatibility layer

**Risk: Pytest API Compatibility**
- **Impact**: pytest internals change between versions affecting test discovery/execution
- **Mitigation**: Use public pytest APIs; extensive version compatibility testing; clear supported version range

**Risk: Performance Degradation at Scale**
- **Impact**: Large test suites cause unacceptable latency or resource consumption
- **Mitigation**: Performance benchmarking; streaming results; pagination for discovery

### Operational Risks

**Risk: PyPI Publishing Automation Failure**
- **Impact**: Release delays; manual intervention required
- **Mitigation**: Comprehensive CI testing of publishing workflow; manual release fallback documented

**Risk: Security Vulnerability in Dependencies**
- **Impact**: CVE disclosure requires rapid response
- **Mitigation**: Automated dependency scanning; rapid patch workflow; security policy documented

### User Experience Risks

**Risk: Installation Friction**
- **Impact**: Users abandon tool due to setup complexity
- **Mitigation**: uvx provides one-command installation; comprehensive documentation; troubleshooting guides

**Risk: AI Assistant Incompatibility**
- **Impact**: Tool works with some MCP clients but not others
- **Mitigation**: Test with multiple MCP client implementations; follow MCP specification strictly

**Risk: Insufficient Argument Coverage**
- **Impact**: AI agents require pytest options not exposed through MCP interface, forcing fallback to shell execution
- **Mitigation**: Comprehensive pytest CLI mapping; extensible parameter validation; clear documentation of supported arguments

## Appendix: Quality Framework Integration

This project adopts the **TRACE Framework** for cognitive load management:

- **T**ype-first thinking: Leverage Python's type system and Pydantic validation to prevent invalid states
- **R**eadability check: Code understandable by new developers within 30 seconds per module
- **A**tomic scope: Changes self-contained with clear boundaries
- **C**ognitive budget: Understanding requires minimal file juggling; clear module responsibilities
- **E**ssential only: Every line justifies its complexity cost; prefer simplicity

**Enhanced Semantic Density Doctrine (E-SDD)**: Documentation and code prioritize precision through sophisticated vocabulary, structural clarity, and maximal meaning per token.

**Parse Don't Validate**: Domain types encode invariants; validation occurs at system boundaries; internal logic operates on proven-valid types.
