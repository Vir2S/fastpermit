from collections.abc import Mapping, Set
from typing import Any

import pytest

from fastpermit import BasicPrincipal, PermissionContext


class CountingBackend:
    def __init__(self) -> None:
        self.calls = 0

    async def get_permissions(
        self,
        principal: BasicPrincipal,
        *,
        scope: Mapping[str, Any],
    ) -> Set[str]:
        self.calls += 1
        return {"project:read", str(scope.get("extra", ""))}


@pytest.mark.asyncio
async def test_context_caches_backend_resolution_per_principal() -> None:
    backend = CountingBackend()
    context = PermissionContext(backend=backend, scope={"extra": "scope:value"})
    principal = BasicPrincipal(id="alice")

    first = await context.get_permissions(principal)
    second = await context.get_permissions(principal)

    assert first == frozenset({"project:read", "scope:value"})
    assert second == first
    assert backend.calls == 1


@pytest.mark.asyncio
async def test_in_memory_backend_mutations(backend, alice) -> None:
    assert await backend.get_permissions(alice, scope={}) == {
        "project:read",
        "project:update",
    }

    backend.grant("alice", "project:delete")
    assert "project:delete" in await backend.get_permissions(alice, scope={})

    backend.revoke("alice", "project:update")
    assert "project:update" not in await backend.get_permissions(alice, scope={})

    backend.set_permissions("alice", {"project:archive"})
    assert await backend.get_permissions(alice, scope={}) == {"project:archive"}

    backend.revoke("missing", "nothing")
