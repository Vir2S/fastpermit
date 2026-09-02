from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastpermit.backends.base import PermissionBackend
from fastpermit.core.context import PermissionContext
from fastpermit.core.permission import BasePermission, Decision
from fastpermit.principal import Principal


@dataclass(slots=True)
class PermissionEvaluator:
    """Evaluate permission expressions independently from any web framework."""

    backend: PermissionBackend

    async def decision(
        self,
        permission: BasePermission,
        principal: Principal | None,
        *,
        scope: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Decision:
        context = self._context(scope=scope, attributes=attributes)
        return await permission.evaluate(principal, context)

    async def check(
        self,
        permission: BasePermission,
        principal: Principal | None,
        *,
        scope: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> bool:
        decision = await self.decision(
            permission,
            principal,
            scope=scope,
            attributes=attributes,
        )
        return decision is True

    async def object_decision(
        self,
        permission: BasePermission,
        principal: Principal | None,
        obj: Any,
        *,
        scope: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Decision:
        context = self._context(scope=scope, attributes=attributes)
        return await permission.evaluate(principal, context, obj=obj)

    async def check_object(
        self,
        permission: BasePermission,
        principal: Principal | None,
        obj: Any,
        *,
        scope: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> bool:
        decision = await self.object_decision(
            permission,
            principal,
            obj,
            scope=scope,
            attributes=attributes,
        )
        return decision is True

    def _context(
        self,
        *,
        scope: Mapping[str, Any] | None,
        attributes: Mapping[str, Any] | None,
    ) -> PermissionContext:
        return PermissionContext(
            backend=self.backend,
            scope=scope or {},
            attributes=attributes or {},
        )
