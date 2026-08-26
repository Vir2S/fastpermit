from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI

from fastpermit import (
    BasePermission,
    BasicPrincipal,
    FastPermit,
    HasPermission,
    HasRole,
    InMemoryBackend,
    PermissionContext,
    Principal,
)

app = FastAPI()

backend = InMemoryBackend(
    {
        "alice": {"project:read", "project:update"},
        "root": {"project:read", "project:update:any"},
    }
)


async def get_current_principal() -> BasicPrincipal:
    return BasicPrincipal(
        id="alice",
        roles=frozenset({"developer"}),
    )


permit = FastPermit(
    backend=backend,
    principal_loader=get_current_principal,
)


@dataclass
class Project:
    id: int
    owner_id: str
    name: str


PROJECTS = {
    1: Project(id=1, owner_id="alice", name="FastPermit"),
    2: Project(id=2, owner_id="bob", name="Another project"),
}


async def get_project(project_id: int) -> Project:
    return PROJECTS[project_id]


class IsOwner(BasePermission):
    async def has_object_permission(
        self,
        principal: Principal | None,
        obj: Project,
        context: PermissionContext,
    ) -> bool:
        del context
        return principal is not None and obj.owner_id == principal.id


edit_project = (
    HasPermission("project:update:any")
    | (
        HasPermission("project:update")
        & IsOwner()
    )
    | HasRole("admin")
)


@app.get("/projects")
async def list_projects(
    principal: Annotated[
        BasicPrincipal,
        Depends(permit.require("project:read")),
    ],
) -> dict[str, str]:
    return {"principal_id": str(principal.id)}


@app.patch("/projects/{project_id}")
async def update_project(
    project: Annotated[
        Project,
        Depends(
            permit.require_object(
                edit_project,
                loader=get_project,
            )
        ),
    ],
) -> Project:
    return project
