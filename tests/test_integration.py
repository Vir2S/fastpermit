from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from fastpermit import (
    BasePermission,
    BasicPrincipal,
    FastPermit,
    HasPermission,
    InMemoryBackend,
    PermissionContext,
    Principal,
)


@dataclass
class Project:
    id: int
    owner_id: str


def create_app(principal: BasicPrincipal | None) -> FastAPI:
    app = FastAPI()
    backend = InMemoryBackend(
        {
            "alice": {"project:read", "project:update"},
            "bob": {"project:update"},
            "admin": {"project:read", "project:update:any"},
        }
    )

    async def principal_loader() -> BasicPrincipal | None:
        return principal

    permit = FastPermit(
        backend=backend,
        principal_loader=principal_loader,
    )

    async def get_project(project_id: int) -> Project:
        return Project(id=project_id, owner_id="alice")

    class IsOwner(BasePermission):
        async def has_object_permission(
            self,
            principal: Principal | None,
            obj: Project,
            context: PermissionContext,
        ) -> bool:
            request = context.attributes["request"]
            assert isinstance(request, Request)
            return principal is not None and principal.id == obj.owner_id

    @app.get("/public")
    async def public() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/projects")
    async def projects(
        current: Any = Depends(permit.require("project:read")),
    ) -> dict[str, str]:
        return {"principal_id": str(current.id)}

    @app.get("/admin")
    async def admin_only(
        current: Any = Depends(permit.require("user:delete")),
    ) -> dict[str, str]:
        return {"principal_id": str(current.id)}

    @app.patch("/projects/{project_id}")
    async def update_project(
        project: Project = Depends(
            permit.require_object(
                HasPermission("project:update") & IsOwner(),
                loader=get_project,
            )
        ),
    ) -> dict[str, int]:
        return {"project_id": project.id}

    return app


def test_require_returns_authorized_principal() -> None:
    app = create_app(BasicPrincipal(id="alice"))
    response = TestClient(app).get("/projects")

    assert response.status_code == 200
    assert response.json() == {"principal_id": "alice"}


def test_require_returns_403_for_authenticated_principal() -> None:
    app = create_app(BasicPrincipal(id="alice"))
    response = TestClient(app).get("/admin")

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied."}


def test_require_returns_401_for_missing_principal() -> None:
    app = create_app(None)
    response = TestClient(app).get("/projects")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_require_returns_401_for_unauthenticated_principal() -> None:
    app = create_app(BasicPrincipal(id="guest", is_authenticated=False))
    response = TestClient(app).get("/projects")

    assert response.status_code == 401


def test_require_object_returns_loaded_object_when_allowed() -> None:
    app = create_app(BasicPrincipal(id="alice"))
    response = TestClient(app).patch("/projects/7")

    assert response.status_code == 200
    assert response.json() == {"project_id": 7}


def test_require_object_returns_403_when_object_rule_denies() -> None:
    app = create_app(BasicPrincipal(id="bob"))
    response = TestClient(app).patch("/projects/7")

    assert response.status_code == 403


def test_invalid_permission_spec_raises_type_error() -> None:
    permit = FastPermit(
        backend=InMemoryBackend(),
        principal_loader=lambda: None,
    )

    try:
        permit.require(123)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "permission must be" in str(exc)
    else:
        raise AssertionError("TypeError was not raised")


def test_require_object_precheck_runs_before_loader() -> None:
    app = FastAPI()
    backend = InMemoryBackend({"alice": {"project:read"}})
    calls = {"loader": 0}

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    async def protected_loader() -> Project:
        calls["loader"] += 1
        return Project(id=1, owner_id="alice")

    permit = FastPermit(backend=backend, principal_loader=principal_loader)

    @app.get("/protected")
    async def protected(
        project: Project = Depends(
            permit.require_object(
                HasPermission("project:update"),
                loader=protected_loader,
            )
        ),
    ) -> dict[str, int]:
        return {"project_id": project.id}

    response = TestClient(app).get("/protected")

    assert response.status_code == 403
    assert calls["loader"] == 0


def test_require_object_denies_fully_neutral_permission() -> None:
    app = FastAPI()
    backend = InMemoryBackend()

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    async def loader() -> Project:
        return Project(id=1, owner_id="alice")

    permit = FastPermit(backend=backend, principal_loader=principal_loader)

    @app.get("/neutral")
    async def neutral(
        project: Project = Depends(
            permit.require_object(
                BasePermission(),
                loader=loader,
            )
        ),
    ) -> dict[str, int]:
        return {"project_id": project.id}

    response = TestClient(app).get("/neutral")

    assert response.status_code == 403


def test_custom_exception_factory_receives_object_phase() -> None:
    app = FastAPI()
    backend = InMemoryBackend({"bob": {"project:update"}})
    phases: list[str] = []

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="bob")

    async def loader() -> Project:
        return Project(id=1, owner_id="alice")

    class IsOwner(BasePermission):
        async def has_object_permission(
            self,
            principal: Principal | None,
            obj: Project,
            context: PermissionContext,
        ) -> bool:
            del context
            return principal is not None and principal.id == obj.owner_id

    def exception_factory(principal, permission, phase):
        del principal, permission
        phases.append(phase)
        return HTTPException(status_code=404, detail="Not found.")

    permit = FastPermit(
        backend=backend,
        principal_loader=principal_loader,
        exception_factory=exception_factory,
    )

    @app.patch("/masked/{project_id}")
    async def masked(
        project: Project = Depends(
            permit.require_object(
                HasPermission("project:update") & IsOwner(),
                loader=loader,
            )
        ),
    ) -> dict[str, int]:
        return {"project_id": project.id}

    response = TestClient(app).patch("/masked/1")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
    assert phases == ["object"]



def test_require_resolves_async_dynamic_scope_from_path_parameter() -> None:
    app = FastAPI()
    seen_scopes: list[Mapping[str, Any]] = []

    class TenantBackend:
        async def get_permissions(
            self,
            principal: Principal,
            *,
            scope: Mapping[str, Any],
        ) -> frozenset[str]:
            del principal
            seen_scopes.append(scope)
            if scope.get("tenant_id") == "acme":
                return frozenset({"project:read"})
            return frozenset()

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    async def tenant_scope(tenant_id: str) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    permit = FastPermit(backend=TenantBackend(), principal_loader=principal_loader)

    @app.get("/tenants/{tenant_id}/projects")
    async def projects(
        principal: BasicPrincipal = Depends(
            permit.require("project:read", scope_loader=tenant_scope)
        ),
    ) -> dict[str, str]:
        return {"principal_id": str(principal.id)}

    allowed = TestClient(app).get("/tenants/acme/projects")
    denied = TestClient(app).get("/tenants/other/projects")

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert seen_scopes == [
        {"tenant_id": "acme"},
        {"tenant_id": "other"},
    ]


def test_require_supports_sync_dynamic_scope_loader() -> None:
    app = FastAPI()

    class TenantBackend:
        async def get_permissions(
            self,
            principal: Principal,
            *,
            scope: Mapping[str, Any],
        ) -> frozenset[str]:
            del principal
            if scope.get("tenant_id") == "acme":
                return frozenset({"project:read"})
            return frozenset()

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    def tenant_scope(tenant_id: str) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    permit = FastPermit(backend=TenantBackend(), principal_loader=principal_loader)

    @app.get("/tenants/{tenant_id}/projects")
    async def projects(
        principal: BasicPrincipal = Depends(
            permit.require("project:read", scope_loader=tenant_scope)
        ),
    ) -> dict[str, str]:
        return {"principal_id": str(principal.id)}

    response = TestClient(app).get("/tenants/acme/projects")

    assert response.status_code == 200


def test_require_object_reuses_dynamic_scope_for_object_permission() -> None:
    app = FastAPI()

    @dataclass
    class TenantProject:
        id: int
        tenant_id: str

    class IsInTenant(BasePermission):
        async def has_object_permission(
            self,
            principal: Principal | None,
            obj: TenantProject,
            context: PermissionContext,
        ) -> bool:
            return (
                principal is not None
                and context.scope.get("tenant_id") == obj.tenant_id
            )

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    async def tenant_scope(tenant_id: str) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    async def loader(tenant_id: str, project_id: int) -> TenantProject:
        return TenantProject(id=project_id, tenant_id=tenant_id)

    permit = FastPermit(backend=InMemoryBackend(), principal_loader=principal_loader)

    @app.get("/tenants/{tenant_id}/projects/{project_id}")
    async def project(
        obj: TenantProject = Depends(
            permit.require_object(
                IsInTenant(),
                loader=loader,
                scope_loader=tenant_scope,
            )
        ),
    ) -> dict[str, Any]:
        return {"id": obj.id, "tenant_id": obj.tenant_id}

    response = TestClient(app).get("/tenants/acme/projects/7")

    assert response.status_code == 200
    assert response.json() == {"id": 7, "tenant_id": "acme"}


def test_scope_and_scope_loader_are_mutually_exclusive() -> None:
    permit = FastPermit(
        backend=InMemoryBackend(),
        principal_loader=lambda: BasicPrincipal(id="alice"),
    )

    async def scope_loader() -> dict[str, str]:
        return {"tenant_id": "acme"}

    with pytest.raises(ValueError, match="cannot be used together"):
        permit.require(
            "project:read",
            scope={"tenant_id": "acme"},
            scope_loader=scope_loader,
        )

    async def loader() -> Project:
        return Project(id=1, owner_id="alice")

    with pytest.raises(ValueError, match="cannot be used together"):
        permit.require_object(
            "project:read",
            loader=loader,
            scope={"tenant_id": "acme"},
            scope_loader=scope_loader,
        )


def test_scope_loader_must_return_mapping() -> None:
    app = FastAPI()

    async def principal_loader() -> BasicPrincipal:
        return BasicPrincipal(id="alice")

    async def invalid_scope_loader() -> str:
        return "acme"

    permit = FastPermit(
        backend=InMemoryBackend({"alice": {"project:read"}}),
        principal_loader=principal_loader,
    )

    @app.get("/invalid-scope")
    async def invalid_scope(
        principal: BasicPrincipal = Depends(
            permit.require(
                "project:read",
                scope_loader=invalid_scope_loader,  # type: ignore[arg-type]
            )
        ),
    ) -> dict[str, str]:
        return {"principal_id": str(principal.id)}

    with pytest.raises(TypeError, match="must return a mapping"):
        TestClient(app).get("/invalid-scope")
