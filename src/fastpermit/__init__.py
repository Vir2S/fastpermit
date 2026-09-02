from importlib.metadata import PackageNotFoundError, version

from fastpermit.backends import InMemoryBackend, PermissionBackend
from fastpermit.core import (
    BasePermission,
    PermissionContext,
    PermissionEvaluator,
    all_of,
    any_of,
)
from fastpermit.integrations import AccessExceptionFactory, AccessPhase, FastPermit, ScopeLoader
from fastpermit.permissions import (
    AllowAny,
    DenyAll,
    HasPermission,
    HasRole,
    IsAuthenticated,
)
from fastpermit.principal import BasicPrincipal, Principal

__all__ = [
    "AccessExceptionFactory",
    "AccessPhase",
    "AllowAny",
    "BasePermission",
    "BasicPrincipal",
    "DenyAll",
    "FastPermit",
    "HasPermission",
    "HasRole",
    "InMemoryBackend",
    "IsAuthenticated",
    "PermissionBackend",
    "PermissionContext",
    "PermissionEvaluator",
    "Principal",
    "ScopeLoader",
    "all_of",
    "any_of",
]

try:
    __version__ = version("fastpermit")
except PackageNotFoundError:  # pragma: no cover - source tree only
    __version__ = "0+unknown"
