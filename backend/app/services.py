"""Business logic. The API layer (api.py) only translates HTTP <-> these calls."""
import logging
import time

from flask import current_app
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from .enrichment import enrich
from .extensions import db
from .metrics import record_event
from .models import Location
from .validation import ValidationError, validate_location

log = logging.getLogger(__name__)

SORT_COLUMNS = {
    "name": Location.name,
    "country": Location.country,
    "type": Location.type,
    "rating": Location.rating,
    "created_at": Location.created_at,
}
ENRICHED_FIELDS = ("description", "image_url", "wiki_url")


class ConflictError(Exception):
    pass


# ---------------------------------------------------------------- queries

def filtered_query(country=None, type_=None, visited=None, search=None, sort="created_at", order="asc"):
    query = Location.query
    if country:
        query = query.filter(func.lower(Location.country) == country.strip().lower())
    if type_:
        query = query.filter(Location.type == type_.strip().lower())
    if visited is not None:
        query = query.filter(Location.visited.is_(visited))
    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(func.lower(Location.name).like(pattern), func.lower(Location.country).like(pattern))
        )

    column = SORT_COLUMNS[sort]
    column = column.desc() if order == "desc" else column.asc()
    # Unrated places go last whichever way you sort; id keeps the order stable.
    return query.order_by(column.nulls_last(), Location.id)


def stats():
    total = Location.query.count()
    visited = Location.query.filter(Location.visited.is_(True)).count()
    average_rating = db.session.query(func.avg(Location.rating)).scalar()
    by_type = dict(
        db.session.query(Location.type, func.count(Location.id)).group_by(Location.type).all()
    )
    by_country = dict(
        db.session.query(Location.country, func.count(Location.id))
        .group_by(Location.country)
        .all()
    )
    by_rating = dict(
        db.session.query(Location.rating, func.count(Location.id))
        .filter(Location.rating.isnot(None))
        .group_by(Location.rating)
        .all()
    )
    return {
        "total": total,
        "visited": visited,
        "wishlist": total - visited,
        "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
        "by_type": by_type,
        "by_country": by_country,
        "by_rating": {str(k): v for k, v in sorted(by_rating.items())},
    }


# ---------------------------------------------------------------- rules

def apply_rating_rule(data, current_visited=False, current_rating=None):
    """Only visited places can have a rating.

    * Sending a rating for a place that is (or will be) on the wishlist -> 422.
    * Moving a rated place back to the wishlist clears its rating.
    """
    visited = data.get("visited", current_visited)
    rating = data["rating"] if "rating" in data else current_rating
    if not visited and rating is not None:
        if data.get("rating") is not None:
            raise ValidationError({"rating": "Only visited locations can be rated."})
        data["rating"] = None
    return data


def _commit():
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError("A location with this name and country already exists.") from exc


# ---------------------------------------------------------------- commands

def create_location(payload):
    data = apply_rating_rule(validate_location(payload))
    location = Location(**data)
    enrich(location)  # skips coordinates if the user typed them in
    db.session.add(location)
    _commit()
    record_event("created")
    log.info("location created", extra={"location_id": location.id})
    return location


def update_location(location, payload, partial=False):
    data = validate_location(payload, partial=partial)
    data = apply_rating_rule(data, location.visited, location.rating)

    renamed = (
        data.get("name", location.name) != location.name
        or data.get("country", location.country) != location.country
    )
    for key, value in data.items():
        setattr(location, key, value)

    if renamed:
        # A different place: old coordinates and description no longer apply.
        if "latitude" not in data:
            location.latitude = location.longitude = None
        for key in ENRICHED_FIELDS:
            setattr(location, key, None)
        enrich(location)

    _commit()
    record_event("updated")
    log.info("location updated", extra={"location_id": location.id})
    return location


def delete_location(location):
    location_id = location.id
    db.session.delete(location)
    db.session.commit()
    record_event("deleted")
    log.info("location deleted", extra={"location_id": location_id})


def refresh_enrichment(location):
    enrich(location, force=True)
    db.session.commit()
    return location


def enrich_missing(limit=50, delay=1.0):
    """Enrich locations that have no coordinates or description yet.

    Used after an import/seed. Nominatim's usage policy allows at most one
    request per second, hence the delay.
    """
    if not current_app.config["ENRICHMENT_ENABLED"]:
        return {"checked": 0, "updated": 0, "remaining": 0}
    missing = Location.query.filter(
        or_(Location.latitude.is_(None), Location.description.is_(None))
    )
    pending = missing.order_by(Location.id).limit(limit).all()
    updated = 0
    for index, location in enumerate(pending):
        if index:
            time.sleep(delay)
        if enrich(location):
            updated += 1
            db.session.commit()
    # Places neither API knows stay "missing"; the client stops when nothing updates.
    return {"checked": len(pending), "updated": updated, "remaining": missing.count()}


def import_locations(items, mode):
    """Import a list of locations. mode is 'append' or 'replace'.

    The whole import is atomic: if any item is invalid nothing is written.
    Duplicates (same name + country) are skipped in append mode.
    Imports do not call external APIs (that could take minutes for a big
    file); run enrich_missing() afterwards.
    """
    if mode not in ("append", "replace"):
        raise ValidationError({"mode": "Must be 'append' or 'replace'."})
    if not isinstance(items, list):
        raise ValidationError({"_schema": "Expected a JSON array of locations."})

    ignored = {"id", "created_at", "updated_at", *ENRICHED_FIELDS}
    cleaned, errors = [], {}
    for index, item in enumerate(items):
        if isinstance(item, dict):
            # Files from /export contain read-only fields; ignore them.
            item = {k: v for k, v in item.items() if k not in ignored}
        try:
            cleaned.append(apply_rating_rule(validate_location(item)))
        except ValidationError as exc:
            errors[str(index)] = exc.errors
    if errors:
        raise ValidationError(errors)

    if mode == "replace":
        Location.query.delete()
        existing = set()
    else:
        existing = {(loc.name.lower(), loc.country.lower()) for loc in Location.query.all()}

    created = skipped = 0
    for data in cleaned:
        key = (data["name"].lower(), data["country"].lower())
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        db.session.add(Location(**data))
        created += 1
    _commit()
    record_event("imported", created)
    log.info("locations imported", extra={"mode": mode, "created_count": created, "skipped_count": skipped})
    return {"mode": mode, "created": created, "skipped": skipped}
