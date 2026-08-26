from typing import Literal, cast

from fastpermit.core.context import PermissionContext
from fastpermit.core.permission import BasePermission, Decision
from fastpermit.principal import Principal

Mode = Literal["all", "any"]


def _validate_mode(mode: str) -> Mode:
    if mode not in ("all", "any"):
        raise ValueError("mode must be 'all' or 'any'.")
    return cast(Mode, mode)


class AllowAny(BasePermission):
    """Always allow the current request."""

    async def has_permission(
        self,
        principal: Principal | None,
        context: PermissionContext,
    ) -> bool:
        del principal, context
        return True


class DenyAll(BasePermission):
    """Always deny the current request."""

    async def has_permission(
        self,
        principal: Principal | None,
        context: PermissionContext,
    ) -> bool:
        del principal, context
        return False


class IsAuthenticated(BasePermission):
    """Allow only authenticated principals."""

    message = "Authentication required."

    async def has_permission(
        self,
        principal: Principal | None,
        context: PermissionContext,
    ) -> bool:
        del context
        return principal is not None and principal.is_authenticated


class HasRole(BasePermission):
    """Require one or more roles already attached to the principal."""

    def __init__(self, *roles: str, mode: str = "any") -> None:
        if not roles:
            raise ValueError("HasRole requires at least one role.")

        self.roles = frozenset(roles)
        self.mode = _validate_mode(mode)

    async def has_permission(
        self,
        principal: Principal | None,
        context: PermissionContext,
    ) -> bool:
        del context
        if principal is None:
            return False

        if self.mode == "all":
            return self.roles.issubset(principal.roles)
        return bool(self.roles.intersection(principal.roles))

    def __repr__(self) -> str:
        roles = ", ".join(sorted(self.roles))
        return f"HasRole({roles}; mode={self.mode})"


class HasPermission(BasePermission):
    """Require effective capability codes resolved by the configured backend."""

    def __init__(self, *permissions: str, mode: str = "all") -> None:
        if not permissions:
            raise ValueError("HasPermission requires at least one permission code.")

        self.permissions = frozenset(permissions)
        self.mode = _validate_mode(mode)

    async def has_permission(
        self,
        principal: Principal | None,
        context: PermissionContext,
    ) -> Decision:
        if principal is None:
            return False

        effective = await context.get_permissions(principal)
        if self.mode == "all":
            return self.permissions.issubset(effective)
        return bool(self.permissions.intersection(effective))

    def __repr__(self) -> str:
        permissions = ", ".join(sorted(self.permissions))
        return f"HasPermission({permissions}; mode={self.mode})"
