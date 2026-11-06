"""Input validation for the REST API.

validate_location() checks each field on its own (type, length, range).
Rules that involve more than one field (e.g. "only visited places can be
rated") live in services.py, because they need the location's current state.
"""

TEXT_FIELDS = {
    # field: (max length, normaliser)
    "name": (120, str.strip),
    "country": (80, str.strip),
    "type": (50, lambda v: v.strip().lower()),
}
REQUIRED_FIELDS = set(TEXT_FIELDS)
COORDINATE_RANGES = {"latitude": (-90.0, 90.0), "longitude": (-180.0, 180.0)}
ALLOWED_FIELDS = REQUIRED_FIELDS | {"visited", "rating"} | set(COORDINATE_RANGES)


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("Validation failed")
        self.errors = errors


def _is_number(value):
    # bool is a subclass of int in Python, so True would otherwise count as 1.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_location(payload, partial=False):
    """Validate a location payload and return a cleaned dict.

    partial=True is used for PATCH: only the supplied fields are checked.
    Raises ValidationError with a {field: message} dict on failure.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"_schema": "Expected a JSON object."})

    errors = {}
    cleaned = {}

    for field in sorted(set(payload) - ALLOWED_FIELDS):
        errors[field] = "Unknown field."

    for field, (max_len, normalise) in TEXT_FIELDS.items():
        if field not in payload:
            if not partial:
                errors[field] = "This field is required."
            continue
        value = payload[field]
        if not isinstance(value, str):
            errors[field] = "Must be a string."
            continue
        value = normalise(value)
        if not value:
            errors[field] = "Must not be empty."
        elif len(value) > max_len:
            errors[field] = f"Must be at most {max_len} characters."
        else:
            cleaned[field] = value

    if "visited" in payload:
        if isinstance(payload["visited"], bool):
            cleaned["visited"] = payload["visited"]
        else:
            errors["visited"] = "Must be true or false."
    elif not partial:
        cleaned["visited"] = False

    if "rating" in payload:
        rating = payload["rating"]
        if rating is None:
            cleaned["rating"] = None
        elif _is_number(rating) and rating == int(rating) and 1 <= rating <= 5:
            cleaned["rating"] = int(rating)
        else:
            errors["rating"] = "Must be a whole number from 1 to 5, or null."

    for field, (low, high) in COORDINATE_RANGES.items():
        if field not in payload:
            continue
        value = payload[field]
        if value is None:
            cleaned[field] = None
        elif _is_number(value) and low <= value <= high:
            cleaned[field] = float(value)
        else:
            errors[field] = f"Must be a number between {low:g} and {high:g}, or null."

    if ("latitude" in cleaned) != ("longitude" in cleaned) and not errors:
        errors["_schema"] = "latitude and longitude must be sent together."

    if partial and not payload:
        errors["_schema"] = "At least one field is required."

    if errors:
        raise ValidationError(errors)
    return cleaned


def parse_bool(value):
    """Parse a query-string boolean; returns None when not a recognised value."""
    if value is None:
        return None
    value = value.strip().lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    return None
