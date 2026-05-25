import json

from django import template

register = template.Library()


@register.filter
def to_json(value):
    if value in (None, ""):
        return "{}"
    return json.dumps(value, indent=2)
