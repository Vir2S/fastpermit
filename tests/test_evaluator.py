import pytest

from fastpermit import HasPermission, PermissionEvaluator


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
