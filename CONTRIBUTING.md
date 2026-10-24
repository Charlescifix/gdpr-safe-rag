# Contributing to GDPR Safe RAG

Thanks for your interest in contributing! This guide covers the basics for local development, quality checks, and pull requests.

## Development Setup

1. Fork and clone the repository.
2. Create and activate a virtual environment.
3. Install development dependencies:

```bash
pip install -e ".[dev]"
```

## Running Quality Checks

Before opening a PR, run the same checks used in CI:

```bash
pytest tests/ -v
ruff check gdpr_safe_rag tests
black --check gdpr_safe_rag tests
mypy gdpr_safe_rag --strict
```

## Pull Request Guidelines

- Keep changes focused and small.
- Include tests for behavior changes.
- Update documentation when APIs or developer workflows change.
- Ensure all checks pass locally.
- Write clear PR titles and descriptions with a short test plan.

## Reporting Issues

When opening an issue, include:

- What you expected to happen
- What actually happened
- Reproduction steps
- Python version and environment details
