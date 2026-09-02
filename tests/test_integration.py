from dataclasses import dataclass
from typing import Any

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
