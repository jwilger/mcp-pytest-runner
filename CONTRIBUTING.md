# Contributing to mcp-pytest-runner

Thank you for your interest in contributing to mcp-pytest-runner!

## Pull Request Process

### PR Title Format (Critical!)

**This project uses squash merges.** Your PR title becomes the commit message on `main`, which drives automated versioning.

PR titles MUST follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <description>
```

**Allowed types and their effects:**

- `feat:` - New feature → **Minor version bump** (0.2.1 → 0.3.0)
- `fix:` - Bug fix → **Patch version bump** (0.2.1 → 0.2.2)
- `docs:` - Documentation only → No version bump
- `style:` - Code style/formatting → No version bump
- `refactor:` - Code restructuring → No version bump
- `perf:` - Performance improvements → No version bump
- `test:` - Test additions/updates → No version bump
- `build:` - Build system changes → No version bump
- `ci:` - CI/CD changes → No version bump
- `chore:` - Maintenance tasks → No version bump
- `revert:` - Revert previous changes → No version bump

**Examples:**
- ✅ `feat: add timeout parameter support`
- ✅ `fix: handle empty test results correctly`
- ✅ `docs: update installation instructions`
- ❌ `Add timeout support` (missing type prefix)
- ❌ `Feature: timeout support` (wrong format)

### Breaking Changes

For breaking changes, include `BREAKING CHANGE:` in the PR description body to trigger a **major version bump** (0.2.1 → 1.0.0).

### PR Title Validation

A GitHub Action automatically validates PR titles. Your PR will fail CI if the title doesn't follow conventional commit format.

## Development Setup

1. Clone the repository
2. Install dependencies with uv:
   ```bash
   uv sync --all-extras
   ```
3. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_execute_tests.py
```

## Code Quality

All code must pass:
- `pytest` - All tests passing
- `mypy` - Type checking in strict mode
- `ruff check` - Linting
- `ruff format` - Code formatting
- `bandit` - Security scanning
- `mutmut` - Mutation testing (≥80% score)

Pre-commit hooks will run these checks automatically.

## Questions?

Open an issue or start a discussion on GitHub!
