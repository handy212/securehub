SCENE_OPTIONS = [
    "House",
    "Apartment",
    "Villa",
    "Commercial",
    "Store",
    "Office",
    "Factory",
    "Hotel",
    "Pharmacy",
    "Restaurant",
    "Community",
    "School",
    "Other",
]


SCENE_ALIASES = {
    "residential": "House",
    "industrial": "Factory",
    "infrastructure": "Community",
    "phamacy": "Pharmacy",
}


def normalize_scene_label(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    canonical = {option.lower(): option for option in SCENE_OPTIONS}
    lowered = raw.lower()

    if lowered in canonical:
        return canonical[lowered]

    if lowered in SCENE_ALIASES:
        return SCENE_ALIASES[lowered]

    titled = raw.title()
    if titled.lower() in canonical:
        return canonical[titled.lower()]

    return "Other"
