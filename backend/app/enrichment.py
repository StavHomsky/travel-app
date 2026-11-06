"""Automatic enrichment of locations from free public APIs.

* Coordinates for the map  -> OpenStreetMap Nominatim (no API key).
* Description + photo       -> Wikipedia REST "page summary" API (no API key).

Enrichment is best-effort: if an API is slow, down, or finds nothing, the
location is still saved, just without that extra data. It can be retried
later with POST /api/v1/locations/<id>/enrich or `flask enrich-db`.
"""
import logging
from urllib.parse import quote

import requests
from flask import current_app

from .metrics import record_enrichment

log = logging.getLogger(__name__)


def _get(url, params=None):
    config = current_app.config
    return requests.get(
        url,
        params=params,
        timeout=config["ENRICHMENT_TIMEOUT"],
        # Both APIs ask clients to identify themselves.
        headers={"User-Agent": config["HTTP_USER_AGENT"], "Accept": "application/json"},
    )


def geocode(name, country):
    """Return (latitude, longitude) for a place, or None."""
    try:
        response = _get(
            current_app.config["GEOCODER_URL"],
            params={"q": f"{name}, {country}", "format": "jsonv2", "limit": 1},
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError):
        log.warning("geocoding failed", extra={"place": name, "country": country}, exc_info=True)
        record_enrichment("geocoder", "error")
        return None

    if not results:
        record_enrichment("geocoder", "not_found")
        return None
    record_enrichment("geocoder", "ok")
    return float(results[0]["lat"]), float(results[0]["lon"])


def wikipedia_summary(name):
    """Return {"description", "image_url", "wiki_url"} for a place, or None."""
    title = quote(name.strip().replace(" ", "_"), safe="")
    try:
        response = _get(f"{current_app.config['WIKIPEDIA_URL']}/page/summary/{title}")
        if response.status_code == 404:
            record_enrichment("wikipedia", "not_found")
            return None
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        log.warning("wikipedia lookup failed", extra={"place": name}, exc_info=True)
        record_enrichment("wikipedia", "error")
        return None

    # "Georgia" could be the country or the US state: Wikipedia returns a
    # disambiguation page, which is no use as a description.
    if data.get("type") == "disambiguation" or not data.get("extract"):
        record_enrichment("wikipedia", "not_found")
        return None

    record_enrichment("wikipedia", "ok")
    image_url = (data.get("thumbnail") or {}).get("source")
    wiki_url = data.get("content_urls", {}).get("desktop", {}).get("page")
    return {
        "description": data["extract"],
        "image_url": image_url if image_url and len(image_url) <= 500 else None,
        "wiki_url": wiki_url if wiki_url and len(wiki_url) <= 500 else None,
    }


def enrich(location, force=False):
    """Fill in missing coordinates/description on a Location (not committed).

    force=True refetches even if the data is already there.
    Returns True if anything changed.
    """
    if not current_app.config["ENRICHMENT_ENABLED"]:
        return False

    changed = False
    if force or location.latitude is None or location.longitude is None:
        coords = geocode(location.name, location.country)
        if coords:
            location.latitude, location.longitude = coords
            changed = True

    if force or location.description is None:
        summary = wikipedia_summary(location.name)
        if summary:
            for key, value in summary.items():
                setattr(location, key, value)
            changed = True

    return changed
