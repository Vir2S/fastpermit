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
