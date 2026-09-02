# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
intends to follow Semantic Versioning once the public API stabilizes.

## [Unreleased]

### Added

- Added request-aware dynamic scopes through the optional `scope_loader` argument on `require()` and `require_object()`.
- Added synchronous and asynchronous scope loader support through FastAPI dependency injection.
- Added a backward-compatibility regression suite covering the public `0.1.x` API.
- Added a documented compatibility policy for additive `0.x` development.
- Exported the public `ScopeLoader` type alias.

### Changed

- Reused one resolved dynamic scope across request prechecks and final object-level authorization.
- Reject simultaneous `scope` and `scope_loader` configuration to keep authorization context unambiguous.

## [0.1.1] - 2026-09-02

### Security

- Deny `HasRole` and `HasPermission` checks for principals marked as unauthenticated.
- Require an explicit allow decision in public evaluator checks and final object authorization.

### Added

- Added a configurable access exception factory with request/object phase information.
- Added generic typing for principal and object dependencies.
- Added PyPI status badge and regression coverage for authorization hardening.
- Added `requirements.txt` for runtime dependencies and `requirements-dev.txt` for development, testing, and packaging dependencies.

### Changed

- Made installed package metadata the single source of truth for `fastpermit.__version__`, with a source-tree fallback.
- Updated the package development classifier from Pre-Alpha to Alpha.
- Modernized collection protocol imports for Python 3.11+.
- Removed Ruff from the mandatory CI and release check gate; linting and formatting remain available as optional local commands.
- Fixed GitHub bug report version placeholders so Issue Forms parse them as strings.
- Included release, security, requirements, and test support files in source distributions.

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
