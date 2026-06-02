from django import template

from apps.guarding.location_utils import object_coordinates, object_location_label, object_maps_url

register = template.Library()


@register.filter
def decoded_location(value):
    return object_location_label(value) or "Unknown location"


@register.filter
def coordinates(value):
    return object_coordinates(value)


@register.filter
def maps_url(value):
    return object_maps_url(value)
