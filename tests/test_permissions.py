import pytest

from fastpermit import (
    AllowAny,
    BasicPrincipal,
    DenyAll,
    HasPermission,
    HasRole,
    IsAuthenticated,
    PermissionEvaluator,
    all_of,
    any_of,
)


@pytest.mark.asyncio
async def test_allow_any_allows_anonymous(backend) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(AllowAny(), None) is True


@pytest.mark.asyncio
async def test_deny_all_denies_authenticated_principal(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(DenyAll(), alice) is False


@pytest.mark.asyncio
async def test_is_authenticated(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(IsAuthenticated(), alice) is True
    assert await evaluator.check(IsAuthenticated(), None) is False

    anonymous = BasicPrincipal(id="anonymous", is_authenticated=False)
    assert await evaluator.check(IsAuthenticated(), anonymous) is False


@pytest.mark.asyncio
async def test_has_role_any_mode(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = HasRole("admin", "developer")
    assert await evaluator.check(permission, alice) is True


@pytest.mark.asyncio
async def test_has_role_all_mode(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(HasRole("developer", mode="all"), alice) is True
    assert await evaluator.check(HasRole("developer", "admin", mode="all"), alice) is False


@pytest.mark.asyncio
async def test_has_permission_all_mode(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = HasPermission("project:read", "project:update")
    assert await evaluator.check(permission, alice) is True


@pytest.mark.asyncio
async def test_has_permission_any_mode(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = HasPermission("user:delete", "project:read", mode="any")
    assert await evaluator.check(permission, alice) is True


@pytest.mark.asyncio
async def test_has_permission_denies_anonymous(backend) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(HasPermission("project:read"), None) is False




@pytest.mark.asyncio
async def test_has_role_denies_unauthenticated_principal(backend) -> None:
    evaluator = PermissionEvaluator(backend)
    anonymous = BasicPrincipal(
        id="anonymous",
        roles=frozenset({"admin"}),
        is_authenticated=False,
    )

    assert await evaluator.check(HasRole("admin"), anonymous) is False


@pytest.mark.asyncio
async def test_has_permission_denies_unauthenticated_principal() -> None:
    calls = {"backend": 0}

    class Backend:
        async def get_permissions(self, principal, *, scope):
            del principal, scope
            calls["backend"] += 1
            return {"project:read"}

    evaluator = PermissionEvaluator(Backend())
    anonymous = BasicPrincipal(id="anonymous", is_authenticated=False)

    assert await evaluator.check(HasPermission("project:read"), anonymous) is False
    assert calls["backend"] == 0


@pytest.mark.asyncio
async def test_and_short_circuits_on_false(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = DenyAll() & HasPermission("project:read")
    assert await evaluator.check(permission, alice) is False


@pytest.mark.asyncio
async def test_or_short_circuits_on_true(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    permission = AllowAny() | HasPermission("missing")
    assert await evaluator.check(permission, alice) is True


@pytest.mark.asyncio
async def test_not_operator(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(~HasRole("admin"), alice) is True
    assert await evaluator.check(~HasRole("developer"), alice) is False


@pytest.mark.asyncio
async def test_all_of_empty_allows(backend) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(all_of(), None) is True


@pytest.mark.asyncio
async def test_any_of_empty_denies(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(any_of(), alice) is False


def test_has_role_validates_arguments() -> None:
    with pytest.raises(ValueError, match="at least one role"):
        HasRole()
    with pytest.raises(ValueError, match="mode"):
        HasRole("admin", mode="invalid")


def test_has_permission_validates_arguments() -> None:
    with pytest.raises(ValueError, match="at least one permission"):
        HasPermission()
    with pytest.raises(ValueError, match="mode"):
        HasPermission("project:read", mode="invalid")


def test_permission_repr() -> None:
    expression = HasRole("admin") | HasPermission("project:read")
    rendered = repr(expression)
    assert "HasRole" in rendered
    assert "HasPermission" in rendered
    assert "|" in rendered
    assert repr(~HasRole("admin")).startswith("~HasRole")


@pytest.mark.asyncio
async def test_all_of_and_any_of_with_multiple_permissions(backend, alice) -> None:
    evaluator = PermissionEvaluator(backend)

    assert await evaluator.check(
        all_of(HasRole("developer"), HasPermission("project:read")),
        alice,
    ) is True
    assert await evaluator.check(
        any_of(HasRole("admin"), HasPermission("project:read")),
        alice,
    ) is True


@pytest.mark.asyncio
async def test_has_role_denies_missing_principal(backend) -> None:
    evaluator = PermissionEvaluator(backend)
    assert await evaluator.check(HasRole("developer"), None) is False


def test_binary_operators_reject_non_permissions() -> None:
    permission = AllowAny()
    with pytest.raises(TypeError, match="AND operand"):
        permission.__and__(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="OR operand"):
        permission.__or__(object())  # type: ignore[arg-type]
    assert repr(permission) == "AllowAny"
