import pytest

from fastpermit import BasePermission, HasPermission, PermissionEvaluator


@pytest.mark.asyncio
async def test_decision_methods_expose_raw_decisions(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)

    assert await evaluator.decision(HasPermission("project:read"), alice) is True
    assert await evaluator.decision(HasPermission("missing"), alice) is False

    assert (
        await evaluator.object_decision(
            HasPermission("project:read"),
            alice,
            object(),
        )
        is True
    )


@pytest.mark.asyncio
async def test_scope_and_attributes_are_forwarded_to_context(alice) -> None:
    captured = {}

    class Backend:
        async def get_permissions(self, principal, *, scope):
            captured.update(scope)
            return {"project:read"}

    evaluator = PermissionEvaluator(Backend())
    assert await evaluator.check(
        HasPermission("project:read"),
        alice,
        scope={"tenant_id": "tenant-1"},
        attributes={"trace_id": "trace-1"},
    )
    assert captured == {"tenant_id": "tenant-1"}


@pytest.mark.asyncio
async def test_check_requires_explicit_allow_decision(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    neutral = BasePermission()

    assert await evaluator.decision(neutral, alice) is None
    assert await evaluator.check(neutral, alice) is False
    assert await evaluator.object_decision(neutral, alice, object()) is None
    assert await evaluator.check_object(neutral, alice, object()) is False
