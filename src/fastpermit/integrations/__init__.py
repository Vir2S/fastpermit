from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, Literal, NoReturn, TypeAlias, TypeVar

from fastapi import Depends, HTTPException, Request, status

from fastpermit.backends.base import PermissionBackend
from fastpermit.core.context import PermissionContext
from fastpermit.core.evaluator import PermissionEvaluator
from fastpermit.core.permission import BasePermission
from fastpermit.permissions import HasPermission
from fastpermit.principal import Principal

PermissionSpec: TypeAlias = BasePermission | str
AccessPhase: TypeAlias = Literal["request", "object"]
AccessExceptionFactory: TypeAlias = Callable[
    [Principal | None, BasePermission, AccessPhase],
    Exception,
]

PrincipalT = TypeVar("PrincipalT", bound=Principal)
ObjectT = TypeVar("ObjectT")


@dataclass(slots=True)
class _AuthorizationState(Generic[PrincipalT]):
    principal: PrincipalT | None
    context: PermissionContext


def _default_access_exception(
    principal: Principal | None,
    permission: BasePermission,
    phase: AccessPhase,
) -> Exception:
    del phase
    if principal is None or not principal.is_authenticated:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=permission.message,
    )


class FastPermit(Generic[PrincipalT]):
    """Framework integration for FastPermit permission expressions."""

    def __init__(
        self,
        *,
        backend: PermissionBackend,
        principal_loader: Callable[
            ...,
            PrincipalT | None | Awaitable[PrincipalT | None],
        ],
        exception_factory: AccessExceptionFactory | None = None,
    ) -> None:
        self.backend = backend
        self.principal_loader = principal_loader
        self.evaluator = PermissionEvaluator(backend)
        self.exception_factory = exception_factory or _default_access_exception

    def require(
        self,
        permission: PermissionSpec,
        *,
        scope: Mapping[str, Any] | None = None,
    ) -> Callable[..., Awaitable[PrincipalT | None]]:
        """Create a dependency that returns the authorized principal."""
        compiled = self._compile(permission)
        principal_loader = self.principal_loader

        async def dependency(
            request: Request,
            principal: PrincipalT | None = Depends(principal_loader),
        ) -> PrincipalT | None:
            allowed = await self.evaluator.check(
                compiled,
                principal,
                scope=scope,
                attributes={"request": request},
            )
            if not allowed:
                self._raise_access_error(principal, compiled, "request")
            return principal

        return dependency

    def require_object(
        self,
        permission: PermissionSpec,
        *,
        loader: Callable[..., ObjectT | Awaitable[ObjectT]],
        scope: Mapping[str, Any] | None = None,
    ) -> Callable[..., Awaitable[ObjectT]]:
        """Pre-check access, load an object, and authorize it."""
        compiled = self._compile(permission)
        principal_loader = self.principal_loader

        async def precheck(
            request: Request,
            principal: PrincipalT | None = Depends(principal_loader),
        ) -> _AuthorizationState[PrincipalT]:
            context = PermissionContext(
                backend=self.backend,
                scope=scope or {},
                attributes={"request": request},
            )
            decision = await compiled.evaluate(principal, context)
            if decision is False:
                self._raise_access_error(principal, compiled, "request")
            return _AuthorizationState(
                principal=principal,
                context=context,
            )

        async def guarded_loader(
            state: _AuthorizationState[PrincipalT] = Depends(precheck),
            obj: ObjectT = Depends(loader),
        ) -> ObjectT:
            del state
            return obj

        async def dependency(
            state: _AuthorizationState[PrincipalT] = Depends(precheck),
            obj: ObjectT = Depends(guarded_loader),
        ) -> ObjectT:
            decision = await compiled.evaluate(
                state.principal,
                state.context,
                obj=obj,
            )
            if decision is not True:
                self._raise_access_error(state.principal, compiled, "object")
            return obj

        return dependency

    @staticmethod
    def _compile(permission: PermissionSpec) -> BasePermission:
        if isinstance(permission, str):
            return HasPermission(permission)
        if isinstance(permission, BasePermission):
            return permission
        raise TypeError("permission must be a permission code or BasePermission instance.")

    def _raise_access_error(
        self,
        principal: Principal | None,
        permission: BasePermission,
        phase: AccessPhase,
    ) -> NoReturn:
        raise self.exception_factory(principal, permission, phase)


__all__ = [
    "AccessExceptionFactory",
    "AccessPhase",
    "FastPermit",
]
