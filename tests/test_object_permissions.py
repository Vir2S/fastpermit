from dataclasses import dataclass

import pytest

from fastpermit import (
    BasePermission,
    HasPermission,
    HasRole,
    PermissionContext,
    PermissionEvaluator,
    Principal,
)


@dataclass
class Project:
    owner_id: str


class IsOwner(BasePermission):
    async def has_object_permission(
        self,
        principal: Principal | None,
        obj: Project,
        context: PermissionContext,
    ) -> bool:
        del context
        return principal is not None and principal.id == obj.owner_id


@pytest.mark.asyncio
async def test_object_only_permission_is_neutral_during_request_phase(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(IsOwner(), alice) is True


@pytest.mark.asyncio
async def test_owner_is_allowed(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check_object(IsOwner(), alice, Project(owner_id="alice")) is True


@pytest.mark.asyncio
async def test_non_owner_is_denied(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check_object(IsOwner(), alice, Project(owner_id="bob")) is False


@pytest.mark.asyncio
async def test_request_and_object_permissions_compose_with_and(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = HasPermission("project:update") & IsOwner()

    assert await evaluator.check_object(permission, alice, Project(owner_id="alice")) is True
    assert await evaluator.check_object(permission, alice, Project(owner_id="bob")) is False


@pytest.mark.asyncio
async def test_request_and_object_permissions_compose_with_or(backend, alice, admin) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = HasRole("admin") | IsOwner()

    assert await evaluator.check(permission, alice) is True
    assert await evaluator.check_object(permission, alice, Project(owner_id="alice")) is True
    assert await evaluator.check_object(permission, alice, Project(owner_id="bob")) is False
    assert await evaluator.check_object(permission, admin, Project(owner_id="bob")) is True


@pytest.mark.asyncio
async def test_not_works_for_object_only_permission(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = ~IsOwner()

    assert await evaluator.check(permission, alice) is True
    assert await evaluator.check_object(permission, alice, Project(owner_id="alice")) is False
    assert await evaluator.check_object(permission, alice, Project(owner_id="bob")) is True


@pytest.mark.asyncio
async def test_complex_expression(backend, alice, admin) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = HasPermission("project:update:any") | (
        HasPermission("project:update") & IsOwner()
    )

    assert await evaluator.check_object(permission, alice, Project(owner_id="alice")) is True
    assert await evaluator.check_object(permission, alice, Project(owner_id="bob")) is False
    assert await evaluator.check_object(permission, admin, Project(owner_id="bob")) is True


@pytest.mark.asyncio
async def test_fully_neutral_permission_stays_neutral(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = BasePermission()

    assert await evaluator.decision(permission, alice) is None
    assert await evaluator.object_decision(permission, alice, Project(owner_id="alice")) is None
    assert await evaluator.check_object(permission, alice, Project(owner_id="alice")) is True


@pytest.mark.asyncio
async def test_neutral_branches_are_preserved_by_boolean_algebra(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    neutral = BasePermission()

    assert await evaluator.decision(HasRole("developer") & neutral, alice) is None
    assert await evaluator.decision(HasRole("missing") | neutral, alice) is None
