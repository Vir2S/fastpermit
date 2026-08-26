from collections.abc import Mapping
from typing import AbstractSet, Any, Protocol

from fastpermit.principal import Principal


class PermissionBackend(Protocol):
    """Storage adapter used to resolve effective permission codes for a principal."""

    async def get_permissions(
        self,
        principal: Principal,
        *,
        scope: Mapping[str, Any],
    ) -> AbstractSet[str]:
        """Return effective permission codes for the principal within the supplied scope."""
        ...
