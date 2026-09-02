from collections.abc import Mapping
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastpermit import (
    AllowAny,
    BasePermission,
    BasicPrincipal,
    FastPermit,
    HasPermission,
    HasRole,
    InMemoryBackend,
    IsAuthenticated,
    PermissionBackend,
    PermissionContext,
    PermissionEvaluator,
    Principal,
    all_of,
    any_of,
)


class ScopeAwareBackend:
    def __init__(self) -> None:
        self.seen_scopes: list[Mapping[str, Any]] = []

    async def get_permissions(
        self,
        principal: Principal,
        *,
        scope: Mapping[str, Any],
    ) -> frozenset[str]:
        del principal
        self.seen_scopes.append(scope)
        if scope.get("tenant_id") == "acme":
            return frozenset({"project:read"})
        return frozenset()


def test_legacy_public_imports_remain_available() -> None:
    assert AllowAny is not None
    assert BasePermission is not None
    assert BasicPrincipal is not None
    assert FastPermit is not None
    assert HasPermission is not None
    assert HasRole is not None
    assert InMemoryBackend is not None
    assert IsAuthenticated is not None
    assert PermissionBackend is not None
    assert PermissionContext is not None
    assert PermissionEvaluator is not None
    assert Principal is not None
    assert all_of is not None
    assert any_of is not None


def test_legacy_constructor_without_new_options_still_works() -> None:
    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    permit = FastPermit(
        backend=InMemoryBackend({"alice": {"project:read"}}),
        principal_loader=principal_loader,
    )

    assert permit.principal_loader is principal_loader


def test_legacy_require_with_static_scope_still_works() -> None:
    app = FastAPI()
    backend = ScopeAwareBackend()

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    permit = FastPermit(backend=backend, principal_loader=principal_loader)

    @app.get("/projects")
    async def projects(
        principal: BasicPrincipal = Depends(
            permit.require(
                "project:read",
                scope={"tenant_id": "acme"},
            )
        ),
    ) -> dict[str, str]:
        return {"principal_id": str(principal.id)}

    response = TestClient(app).get("/projects")

    assert response.status_code == 200
    assert response.json() == {"principal_id": "alice"}
    assert backend.seen_scopes == [{"tenant_id": "acme"}]


def test_legacy_require_object_signature_still_works() -> None:
    app = FastAPI()

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    async def loader() -> dict[str, str]:
        return {"id": "project-1"}

    permit = FastPermit(
        backend=InMemoryBackend({"alice": {"project:read"}}),
        principal_loader=principal_loader,
    )

    @app.get("/projects/project-1")
    async def project(
        obj: dict[str, str] = Depends(
            permit.require_object(
                HasPermission("project:read"),
                loader=loader,
                scope={"tenant_id": "acme"},
            )
        ),
    ) -> dict[str, str]:
        return obj

    response = TestClient(app).get("/projects/project-1")

    assert response.status_code == 200
    assert response.json() == {"id": "project-1"}


def test_legacy_permission_algebra_remains_unchanged() -> None:
    permission = (
        IsAuthenticated()
        & HasPermission("project:update")
        & (HasRole("admin") | HasPermission("project:update:any"))
    )

    rendered = repr(permission)
    assert "&" in rendered
    assert "|" in rendered
    assert "HasPermission" in rendered
    assert "HasRole" in rendered
