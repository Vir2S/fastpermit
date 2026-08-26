from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import AbstractSet, Any, Hashable, Protocol, runtime_checkable


@runtime_checkable
class Principal(Protocol):
    """Minimal read-only identity contract consumed by FastPermit."""

    @property
    def id(self) -> Hashable:
        """Stable identifier used by permission backends."""
        ...

    @property
    def roles(self) -> AbstractSet[str]:
        """Roles already attached to the principal by the application."""
        ...

    @property
    def attributes(self) -> Mapping[str, Any]:
        """Application-defined identity attributes available to custom rules."""
        ...

    @property
    def is_authenticated(self) -> bool:
        """Whether the application considers this principal authenticated."""
        ...


@dataclass(frozen=True, slots=True)
class BasicPrincipal:
    """Small concrete principal implementation for common applications and tests."""

    id: Hashable
    roles: frozenset[str] = field(default_factory=frozenset)
    attributes: Mapping[str, Any] = field(default_factory=dict)
    is_authenticated: bool = True
