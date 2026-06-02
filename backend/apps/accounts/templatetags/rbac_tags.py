from django import template

from apps.accounts.permissions import user_has_console_permission

register = template.Library()


@register.filter(name="has_console_perm")
def has_console_perm(user, permission: str) -> bool:
    return user_has_console_permission(user, permission)


@register.simple_tag(takes_context=True)
def console_can(context, permission: str) -> bool:
    request = context.get("request")
    if not request:
        return False
    return user_has_console_permission(request.user, permission)
