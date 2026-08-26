from fastpermit.core.permission import BasePermission
from fastpermit.permissions import AllowAny, DenyAll


def all_of(*permissions: BasePermission) -> BasePermission:
    """Combine rules with logical AND; an empty set allows access."""
    if not permissions:
        return AllowAny()

    result = permissions[0]
    for permission in permissions[1:]:
        result = result & permission
    return result


def any_of(*permissions: BasePermission) -> BasePermission:
    """Combine rules with logical OR; an empty set denies access."""
    if not permissions:
        return DenyAll()

    result = permissions[0]
    for permission in permissions[1:]:
        result = result | permission
    return result
