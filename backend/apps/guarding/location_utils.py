def format_coordinates(latitude, longitude) -> str:
    if latitude is None or longitude is None:
        return ""
    try:
        return f"{float(latitude):.6f}, {float(longitude):.6f}"
    except (TypeError, ValueError):
        return f"{latitude}, {longitude}"


def maps_url(latitude, longitude) -> str:
    coords = format_coordinates(latitude, longitude)
    if not coords:
        return ""
    return f"https://www.google.com/maps?q={coords.replace(' ', '')}"


def site_address_label(site) -> str:
    if site is None:
        return ""
    parts = [
        getattr(site, "address", ""),
        getattr(site, "city", ""),
        getattr(site, "state", ""),
        getattr(site, "country", ""),
    ]
    return ", ".join(part for part in parts if part)


def site_location_label(site) -> str:
    if site is None:
        return ""
    address = site_address_label(site)
    if address:
        return f"{site.name} - {address}"
    return str(site)


def post_location_label(post) -> str:
    if post is None:
        return ""
    site = getattr(post, "site", None)
    if site:
        return f"{post.name} - {site_location_label(site)}"
    return str(post)


def checkpoint_location_label(checkpoint) -> str:
    if checkpoint is None:
        return ""
    post = getattr(checkpoint, "post", None)
    if post:
        return f"{checkpoint.name} - {post_location_label(post)}"
    return str(checkpoint)


def assignment_location_label(assignment) -> str:
    if assignment is None:
        return ""
    shift = getattr(assignment, "shift", None)
    return post_location_label(getattr(shift, "post", None))


def object_location_label(obj) -> str:
    if obj is None:
        return ""
    if hasattr(obj, "assignment") and getattr(obj, "assignment", None):
        return assignment_location_label(obj.assignment)
    if hasattr(obj, "checkpoint") and getattr(obj, "checkpoint", None):
        return checkpoint_location_label(obj.checkpoint)
    if hasattr(obj, "post") and getattr(obj, "post", None):
        return post_location_label(obj.post)
    if hasattr(obj, "site") and getattr(obj, "site", None):
        return site_location_label(obj.site)
    if hasattr(obj, "route") and getattr(obj, "route", None):
        return post_location_label(getattr(obj.route, "post", None))
    if hasattr(obj, "guard") and getattr(obj, "guard", None):
        return f"GPS location for {obj.guard.full_name}"
    return ""


def object_coordinates(obj) -> str:
    return format_coordinates(
        getattr(obj, "latitude", None),
        getattr(obj, "longitude", None),
    )


def object_maps_url(obj) -> str:
    return maps_url(
        getattr(obj, "latitude", None),
        getattr(obj, "longitude", None),
    )
