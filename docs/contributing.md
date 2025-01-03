# Contributing Guidelines

We welcome contributions from the community! This guide will help you understand our contribution process and requirements.

## Development guidelines

1. Small PRs ([blogpost](https://testing.googleblog.com/2024/07/in-praise-of-small-pull-requests.html))
1. When fixing a bug, include a test that reproduces the issue in the same pull request (the test should fail without your changes)
1. If you are refactoring, ensure adequate test coverage exists for the target area. If coverage is insufficient, create tests in a separate pull request first. This approach provides a safety net for validating current behavior and simplifies code reviews.

## Build and Test

Prerequisites:

- Poetry 1.5.1 [Installation guide](https://python-poetry.org/docs/#installing-with-the-official-installer)

### Install dependencies

```bash
poetry install
```

### Unit tests

```bash
poetry run pytest tests/unit
```

### Linting and Type-checking

`solnlib` uses the [`pre-commit`](https://pre-commit.com) framework for linting and type-checking.
Consult with `pre-commit` documentation about what is the best way to install the software.

To run it locally:

```bash
pre-commit run --all-files
```
