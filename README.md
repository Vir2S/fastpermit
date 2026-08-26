# FastPermit

[![CI](https://github.com/Vir2S/fastpermit/actions/workflows/ci.yml/badge.svg)](https://github.com/Vir2S/fastpermit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Composable, backend-agnostic authorization for FastAPI.**

FastPermit keeps authentication and authorization separate. Your application authenticates a
principal with JWT, OAuth2, Auth0, Keycloak, FastAPI Users, or a custom mechanism. FastPermit then
decides whether that principal may perform an action.

The core is deliberately small:

- composable permissions with `&`, `|`, and `~`;
- request-level and object-level authorization;
- role-based access control (RBAC) primitives;
- pluggable permission backends;
- async-first execution;
- FastAPI dependency integration;
- no ORM or cache dependency in the core.

> Status: `0.1.0` — first public release.

## Project status

FastPermit is in active early development. The `0.1.x` line focuses on a small, typed,
backend-agnostic core before adding optional persistence and caching adapters.

Planned next steps:

- SQLAlchemy 2 / PostgreSQL adapter;
- Redis permission cache and invalidation hooks;
- tenant and resource scopes;
- audit and observability hooks.

## Installation

Install from PyPI:

```bash
pip install fastpermit
```

For development:

```bash
git clone https://github.com/Vir2S/fastpermit.git
cd fastpermit
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make check
```

## Quick start

```python
from typing import Annotated

from fastapi import Depends, FastAPI

from fastpermit import BasicPrincipal, FastPermit, HasPermission, InMemoryBackend

app = FastAPI()

backend = InMemoryBackend(
    {
        "user-1": {"project:read", "project:update"},
    }
)


async def get_current_principal() -> BasicPrincipal:
    # Replace this with JWT, OAuth2, Auth0, Keycloak, or your own authentication.
    return BasicPrincipal(id="user-1", roles=frozenset({"developer"}))


permit = FastPermit(
    backend=backend,
    principal_loader=get_current_principal,
)


@app.get("/projects")
async def list_projects(
    principal: Annotated[
        BasicPrincipal,
        Depends(permit.require("project:read")),
    ],
) -> dict[str, str]:
    return {"principal_id": str(principal.id)}
```

A string passed to `require()` is shorthand for `HasPermission(...)`:

```python
Depends(permit.require("project:read"))
```

is equivalent to:

```python
Depends(permit.require(HasPermission("project:read")))
```

## Permission algebra

Permissions can be combined without putting authorization branches in route handlers:

```python
from fastpermit import HasPermission, HasRole, IsAuthenticated

permission = (
    IsAuthenticated()
    & HasPermission("project:update")
    & (
        HasRole("admin")
        | HasPermission("project:update:any")
    )
)
```

Supported operators:

```python
A() & B()   # AND
A() | B()   # OR
~A()        # NOT
```

The helpers `all_of()` and `any_of()` are available for larger expressions:

```python
from fastpermit import all_of, any_of

permission = all_of(
    IsAuthenticated(),
    HasPermission("project:update"),
    any_of(
        HasRole("admin"),
        HasRole("manager"),
    ),
)
```

## Object-level permissions

Object rules are intentionally separate from loading the object. A custom rule only needs to
implement `has_object_permission()`:

```python
from typing import Any

from fastpermit import BasePermission, PermissionContext, Principal


class IsOwner(BasePermission):
    async def has_object_permission(
        self,
        principal: Principal | None,
        obj: Any,
        context: PermissionContext,
    ) -> bool:
        return principal is not None and obj.owner_id == principal.id
```

Then combine it with ordinary permissions:

```python
edit_project = (
    HasPermission("project:update:any")
    | (
        HasPermission("project:update")
        & IsOwner()
    )
)
```

Use it with a FastAPI loader dependency:

```python
@app.patch("/projects/{project_id}")
async def update_project(
    project=Depends(
        permit.require_object(
            edit_project,
            loader=get_project,
        )
    ),
):
    return project
```

FastPermit evaluates both request-level and object-level branches as a single expression. Rules
that do not apply during a phase are neutral rather than implicitly allowing or denying it. This
keeps expressions such as `HasRole("admin") | IsOwner()` and `~IsOwner()` logically correct.

## Principals

FastPermit uses a small `Principal` protocol rather than a concrete user model. The included
`BasicPrincipal` is convenient for most applications:

```python
from fastpermit import BasicPrincipal

principal = BasicPrincipal(
    id="user-42",
    roles=frozenset({"manager", "reviewer"}),
    attributes={"organization_id": "org-1"},
)
```

You may return your own object from the authentication dependency as long as it exposes:

```text
id
roles
attributes
is_authenticated
```

## Backends

A backend answers one question: which permission codes are effective for this principal in this
scope?

```python
from collections.abc import Mapping
from typing import AbstractSet, Any

from fastpermit import PermissionBackend, Principal


class MyBackend(PermissionBackend):
    async def get_permissions(
        self,
        principal: Principal,
        *,
        scope: Mapping[str, Any],
    ) -> AbstractSet[str]:
        ...
```

`InMemoryBackend` is included for tests, prototypes, and examples. SQLAlchemy/PostgreSQL and Redis
adapters are intentionally planned as optional integrations instead of core requirements.

## Request context and scopes

A permission receives `PermissionContext`, which contains:

- the configured backend;
- a scope mapping;
- integration-specific attributes;
- a per-evaluation permission cache.

FastAPI integration exposes the current `Request` as `context.attributes["request"]` without
making the authorization core depend on FastAPI.

Static scope can be attached to a dependency:

```python
Depends(
    permit.require(
        "billing:read",
        scope={"tenant": "global"},
    )
)
```

Dynamic tenant scopes are planned for the next integration iteration.

## HTTP semantics

FastPermit does not authenticate requests. Authentication remains the responsibility of your
principal loader.

When a FastPermit rule denies access:

- an absent or unauthenticated principal produces `401 Unauthorized`;
- an authenticated principal without sufficient authorization produces `403 Forbidden`.

## Design principles

1. Authentication and authorization are separate concerns.
2. Routes should describe required access, not implement role branches.
3. Permission codes are stable capabilities such as `project:update`.
4. Roles aggregate capabilities; application code should not be coupled to role names where a
   capability is the real requirement.
5. Object-level rules belong in permissions, not route handlers.
6. Storage and caching are adapters, not core concerns.
7. Authorization expressions must preserve correct semantics across request and object phases.

## Roadmap

### 0.1

- [x] permission core;
- [x] `AND`, `OR`, `NOT` composition;
- [x] `all_of()` / `any_of()`;
- [x] `IsAuthenticated`;
- [x] `HasRole`;
- [x] `HasPermission`;
- [x] object-level permissions;
- [x] backend protocol;
- [x] in-memory backend;
- [x] FastAPI integration;
- [x] typed package;
- [x] tests and CI.

### 0.2

- [ ] SQLAlchemy 2.x adapter;
- [ ] PostgreSQL RBAC reference models;
- [ ] Alembic examples;
- [ ] user-role and role-permission repositories.

### 0.3

- [ ] Redis cache adapter;
- [ ] cache invalidation primitives;
- [ ] cache versioning;
- [ ] configurable TTL policies.

### 0.4

- [ ] dynamic tenant scopes;
- [ ] attribute-based access control helpers;
- [ ] resource scopes;
- [ ] policy metadata.

### 0.5

- [ ] authorization audit events;
- [ ] observability hooks;
- [ ] OpenTelemetry integration.

## License

MIT

## Maintainer

Created and maintained by [Vitaly Sem](https://github.com/Vir2S).

FastPermit is an independent open-source project developed with support from Born2CodeLab.
