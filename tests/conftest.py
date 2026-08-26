import pytest

from fastpermit import BasicPrincipal, InMemoryBackend


@pytest.fixture
def backend() -> InMemoryBackend:
    return InMemoryBackend(
        {
            "alice": {"project:read", "project:update"},
            "admin": {"project:read", "project:update:any", "user:delete"},
        }
    )


@pytest.fixture
def alice() -> BasicPrincipal:
    return BasicPrincipal(
        id="alice",
        roles=frozenset({"developer"}),
        attributes={"organization_id": "org-1"},
    )


@pytest.fixture
def admin() -> BasicPrincipal:
    return BasicPrincipal(
        id="admin",
        roles=frozenset({"admin"}),
    )
