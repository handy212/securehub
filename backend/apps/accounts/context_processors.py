from apps.accounts.permissions import get_operator_role, user_has_console_permission
from apps.accounts.rbac import Perm, permissions_for_role


def console_rbac(request):
    defaults = {
        "console_operator_role": None,
        "console_permissions": frozenset(),
        "console_can": lambda perm: False,
        "console_perm": Perm,
    }
    if not request.user.is_authenticated or not request.user.is_staff:
        return defaults
    role = get_operator_role(request.user)
    granted = permissions_for_role(role) if role else frozenset()
    return {
        "console_operator_role": role,
        "console_permissions": granted,
        "console_can": lambda perm: user_has_console_permission(request.user, perm),
        "console_perm": Perm,
    }
