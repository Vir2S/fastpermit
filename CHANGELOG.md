# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
intends to follow Semantic Versioning once the public API stabilizes.

## [Unreleased]

## [0.1.0] - 2026-08-26

### Changed

- Flattened the framework integration into `fastpermit.integrations` so framework names no longer appear in internal module paths.
- Updated package and documentation metadata for the first public release.

### Added

- PyPI Trusted Publishing release workflow using GitHub OIDC.
- Release documentation and tag/version verification.
- Public repository metadata, maintainer information, CI badges, and security policy.
- Request-level prechecks for object dependencies so denied requests do not load protected resources.
- Source and wheel packaging configuration with typed-package marker support.
- Initial FastPermit package scaffold.
- Backend-agnostic permission core.
- Three-state permission evaluation for correct request/object composition.
- `AND`, `OR`, and `NOT` permission operators.
- `all_of()` and `any_of()` helpers.
- `Principal` protocol and `BasicPrincipal` implementation.
- `PermissionBackend` protocol and `InMemoryBackend`.
- Built-in `AllowAny`, `DenyAll`, `IsAuthenticated`, `HasRole`, and `HasPermission` rules.
- Framework `require()` and `require_object()` integrations.
- Unit and integration test suites.
- Ruff, mypy, pytest, coverage, build, and GitHub Actions configuration.
