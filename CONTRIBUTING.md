# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Run the complete local quality gate:

```bash
make check
```

Individual commands:

```bash
make lint
make format-check
make typecheck
make test
make build
```

## Pull requests

- Keep the permission core independent from storage and authentication implementations.
- Add tests for every behavior change.
- Add user-facing changes to `CHANGELOG.md`, newest entries first.
- Keep public APIs fully typed.
- Use English for code comments and docstrings.

## Compatibility policy

The public API introduced in `0.1.x` is the compatibility baseline for future `0.x` releases.
Contributions should prefer additive changes and must not silently break existing applications.

- Do not remove or rename existing public imports.
- Do not change the meaning of existing constructor or method arguments.
- Add new arguments as optional keyword arguments with backward-compatible defaults.
- Keep static `scope={...}` authorization supported when adding dynamic scope features.
- Keep database, cache, and identity-provider integrations outside the authorization core.
- Add or update `tests/test_backward_compatibility.py` whenever a public API changes.
- If a breaking change ever becomes unavoidable, deprecate it first and document the migration.
  Intentional public API removals are not planned before `1.0`.
