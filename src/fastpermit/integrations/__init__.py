from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias, cast

from fastapi import Depends, HTTPException, Request, status

from fastpermit.backends.base import PermissionBackend
from fastpermit.core.context import PermissionContext
from fastpermit.core.evaluator import PermissionEvaluator
from fastpermit.core.permission import BasePermission
from fastpermit.permissions import HasPermission
from fastpermit.principal import Principal

PermissionSpec: TypeAlias = BasePermission | str
PrincipalLoader: TypeAlias = Callable[..., Any]
ObjectLoader: TypeAlias = Callable[..., Any]


@dataclass(slots=True)
class _AuthorizationState:
    principal: Principal | None
    context: PermissionContext


class FastPermit:
    """Framework integration for FastPermit permission expressions."""

    def __init__(
        self,
        *,
        backend: PermissionBackend,
        principal_loader: PrincipalLoader,
    ) -> None:
        self.backend = backend
        self.principal_loader = principal_loader
        self.evaluator = PermissionEvaluator(backend)

    def require(
        self,
        permission: PermissionSpec,
        *,
        scope: Mapping[str, Any] | None = None,
    ) -> Callable[..., Any]:
        """Create a dependency that returns the authorized principal."""
        compiled = self._compile(permission)
        principal_loader = self.principal_loader

        async def dependency(
            request: Request,
            principal: Any = Depends(principal_loader),
        ) -> Any:
            typed_principal = cast(Principal | None, principal)
            allowed = await self.evaluator.check(
                compiled,
                typed_principal,
                scope=scope,
                attributes={"request": request},
            )
            if not allowed:
                self._raise_access_error(typed_principal, compiled)
            return principal

        return dependency

    def require_object(
        self,
        permission: PermissionSpec,
        *,
        loader: ObjectLoader,
        scope: Mapping[str, Any] | None = None,
    ) -> Callable[..., Any]:
        """Pre-check access, load an object, and authorize it."""
        compiled = self._compile(permission)
        principal_loader = self.principal_loader

        async def precheck(
            request: Request,
            principal: Any = Depends(principal_loader),
        ) -> _AuthorizationState:
            typed_principal = cast(Principal | None, principal)
            context = PermissionContext(
                backend=self.backend,
                scope=scope or {},
                attributes={"request": request},
            )
            decision = await compiled.evaluate(typed_principal, context)
            if decision is False:
                self._raise_access_error(typed_principal, compiled)
            return _AuthorizationState(
                principal=typed_principal,
                context=context,
            )

        async def guarded_loader(
            state: _AuthorizationState = Depends(precheck),
            obj: Any = Depends(loader),
        ) -> Any:
            del state
            return obj

        async def dependency(
            state: _AuthorizationState = Depends(precheck),
            obj: Any = Depends(guarded_loader),
        ) -> Any:
            decision = await compiled.evaluate(
                state.principal,
                state.context,
                obj=obj,
            )
            if decision is False:
                self._raise_access_error(state.principal, compiled)
            return obj

        return dependency

    @staticmethod
    def _compile(permission: PermissionSpec) -> BasePermission:
        if isinstance(permission, str):
            return HasPermission(permission)
        if isinstance(permission, BasePermission):
            return permission
        raise TypeError("permission must be a permission code or BasePermission instance.")

    @staticmethod
    def _raise_access_error(
        principal: Principal | None,
        permission: BasePermission,
    ) -> None:
        if principal is None or not principal.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=permission.message,
        )


__all__ = ["FastPermit"]
