from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from typing import Any

from fastpermit.backends.base import PermissionBackend
from fastpermit.principal import Principal


@dataclass(slots=True)
class PermissionContext:
    """Evaluation context shared by every rule in one authorization decision."""

    backend: PermissionBackend
    scope: Mapping[str, Any] = field(default_factory=dict)
    attributes: Mapping[str, Any] = field(default_factory=dict)
    _permissions_cache: dict[Hashable, frozenset[str]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    async def get_permissions(self, principal: Principal) -> frozenset[str]:
        """Resolve effective permissions once per principal and evaluation context."""
        cached = self._permissions_cache.get(principal.id)
        if cached is not None:
            return cached

        resolved = frozenset(
            await self.backend.get_permissions(
                principal,
                scope=self.scope,
            )
        )
        self._permissions_cache[principal.id] = resolved
        return resolved
