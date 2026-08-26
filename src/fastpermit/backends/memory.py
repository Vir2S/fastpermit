from collections.abc import Iterable, Mapping
from typing import AbstractSet, Any, Hashable

from fastpermit.principal import Principal


class InMemoryBackend:
    """Mutable in-memory permission backend intended for tests and prototypes."""

    def __init__(
        self,
        permissions: Mapping[Hashable, Iterable[str]] | None = None,
    ) -> None:
        self._permissions: dict[Hashable, set[str]] = {
            principal_id: set(codes)
            for principal_id, codes in (permissions or {}).items()
        }

    async def get_permissions(
        self,
        principal: Principal,
        *,
        scope: Mapping[str, Any],
    ) -> AbstractSet[str]:
        del scope
        return frozenset(self._permissions.get(principal.id, set()))

    def set_permissions(
        self,
        principal_id: Hashable,
        permissions: Iterable[str],
    ) -> None:
        self._permissions[principal_id] = set(permissions)

    def grant(self, principal_id: Hashable, *permissions: str) -> None:
        self._permissions.setdefault(principal_id, set()).update(permissions)

    def revoke(self, principal_id: Hashable, *permissions: str) -> None:
        current = self._permissions.get(principal_id)
        if current is None:
            return
        current.difference_update(permissions)
