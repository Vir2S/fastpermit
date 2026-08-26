from __future__ import annotations

from typing import Any, Final, TypeAlias

from fastpermit.core.context import PermissionContext
from fastpermit.principal import Principal

Decision: TypeAlias = bool | None
_OBJECT_MISSING: Final = object()


def _and_decisions(left: Decision, right: Decision) -> Decision:
    if left is False or right is False:
        return False
    if left is True and right is True:
        return True
    return None


def _or_decisions(left: Decision, right: Decision) -> Decision:
    if left is True or right is True:
        return True
    if left is False and right is False:
        return False
    return None


def _not_decision(value: Decision) -> Decision:
    if value is None:
        return None
    return not value


def _combine_phases(request: Decision, object_: Decision) -> Decision:
    if request is False or object_ is False:
        return False
    if request is None and object_ is None:
        return None
    return True


class BasePermission:
    """Base class for request-level, object-level, and composite permission rules.

    Returning ``None`` means the rule is neutral for that evaluation phase. This allows
    request-only and object-only rules to compose correctly with AND, OR, and NOT.
    """

    message = "Permission denied."

    async def has_permission(
        self,
        principal: Principal | None,
        context: PermissionContext,
    ) -> Decision:
        """Evaluate a request-level rule or return None when the rule is object-only."""
        del principal, context
        return None

    async def has_object_permission(
        self,
        principal: Principal | None,
        obj: Any,
        context: PermissionContext,
    ) -> Decision:
        """Evaluate an object-level rule or return None when the rule is request-only."""
        del principal, obj, context
        return None

    async def evaluate(
        self,
        principal: Principal | None,
        context: PermissionContext,
        *,
        obj: Any = _OBJECT_MISSING,
    ) -> Decision:
        """Evaluate this rule for the current request and optional resource object."""
        request_decision = await self.has_permission(principal, context)
        if obj is _OBJECT_MISSING:
            return request_decision

        object_decision = await self.has_object_permission(principal, obj, context)
        return _combine_phases(request_decision, object_decision)

    def __and__(self, other: BasePermission) -> BasePermission:
        if not isinstance(other, BasePermission):
            raise TypeError("AND operand must be a BasePermission instance.")
        return _AndPermission(self, other)

    def __or__(self, other: BasePermission) -> BasePermission:
        if not isinstance(other, BasePermission):
            raise TypeError("OR operand must be a BasePermission instance.")
        return _OrPermission(self, other)

    def __invert__(self) -> BasePermission:
        return _NotPermission(self)

    def __repr__(self) -> str:
        return self.__class__.__name__


class _BinaryPermission(BasePermission):
    operator = "?"

    def __init__(self, left: BasePermission, right: BasePermission) -> None:
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"({self.left!r} {self.operator} {self.right!r})"


class _AndPermission(_BinaryPermission):
    operator = "&"

    async def evaluate(
        self,
        principal: Principal | None,
        context: PermissionContext,
        *,
        obj: Any = _OBJECT_MISSING,
    ) -> Decision:
        left = await self.left.evaluate(principal, context, obj=obj)
        if left is False:
            return False

        right = await self.right.evaluate(principal, context, obj=obj)
        return _and_decisions(left, right)


class _OrPermission(_BinaryPermission):
    operator = "|"

    async def evaluate(
        self,
        principal: Principal | None,
        context: PermissionContext,
        *,
        obj: Any = _OBJECT_MISSING,
    ) -> Decision:
        left = await self.left.evaluate(principal, context, obj=obj)
        if left is True:
            return True

        right = await self.right.evaluate(principal, context, obj=obj)
        return _or_decisions(left, right)


class _NotPermission(BasePermission):
    def __init__(self, permission: BasePermission) -> None:
        self.permission = permission

    async def evaluate(
        self,
        principal: Principal | None,
        context: PermissionContext,
        *,
        obj: Any = _OBJECT_MISSING,
    ) -> Decision:
        decision = await self.permission.evaluate(principal, context, obj=obj)
        return _not_decision(decision)

    def __repr__(self) -> str:
        return f"~{self.permission!r}"
