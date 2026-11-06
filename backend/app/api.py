"""REST API (Flask-RESTful), mounted at /api/v1.

Every error response has the same shape:
    {"error": "<HTTP reason>", "message": "<human text>", "details": {...}}
"""
import json
from functools import wraps
from http import HTTPStatus

from flask import Blueprint, request
from flask_restful import Api, Resource, abort

from . import services
from .extensions import db
from .models import Location
from .validation import ValidationError, parse_bool

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
api = Api(api_bp)

MAX_PER_PAGE = 100


def api_error(status, message, details=None):
    abort(status, error=HTTPStatus(status).phrase, message=message, details=details or {})


def handle_service_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as exc:
            api_error(422, "Validation failed.", exc.errors)
        except services.ConflictError as exc:
            api_error(409, str(exc))

    return wrapper


def get_json_body():
    data = request.get_json(silent=True)
    if data is None:
        api_error(400, "Request body must be valid JSON with Content-Type: application/json.")
    return data


def get_location_or_404(location_id):
    location = db.session.get(Location, location_id)
    if location is None:
        api_error(404, f"Location {location_id} not found.")
    return location


def int_arg(name, default, minimum, maximum):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        api_error(400, "Invalid query parameter.", {name: "Must be an integer."})
    if not minimum <= value <= maximum:
        api_error(400, "Invalid query parameter.", {name: f"Must be between {minimum} and {maximum}."})
    return value


class LocationListResource(Resource):
    method_decorators = [handle_service_errors]

    def get(self):
        visited_raw = request.args.get("visited")
        visited = parse_bool(visited_raw)
        if visited_raw is not None and visited is None:
            api_error(400, "Invalid query parameter.", {"visited": "Must be true or false."})

        sort = request.args.get("sort", "created_at")
        if sort not in services.SORT_COLUMNS:
            allowed = ", ".join(sorted(services.SORT_COLUMNS))
            api_error(400, "Invalid query parameter.", {"sort": f"Must be one of: {allowed}."})
        order = request.args.get("order", "asc")
        if order not in ("asc", "desc"):
            api_error(400, "Invalid query parameter.", {"order": "Must be 'asc' or 'desc'."})

        page = int_arg("page", 1, 1, 10_000)
        per_page = int_arg("per_page", 20, 1, MAX_PER_PAGE)
        query = services.filtered_query(
            country=request.args.get("country"),
            type_=request.args.get("type"),
            visited=visited,
            search=request.args.get("q"),
            sort=sort,
            order=order,
        )
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "items": [loc.to_dict() for loc in result.items],
            "page": page,
            "per_page": per_page,
            "total": result.total,
            "pages": result.pages,
        }

    def post(self):
        location = services.create_location(get_json_body())
        return location.to_dict(), 201, {"Location": f"/api/v1/locations/{location.id}"}


class LocationResource(Resource):
    method_decorators = [handle_service_errors]

    def get(self, location_id):
        return get_location_or_404(location_id).to_dict()

    def put(self, location_id):
        location = get_location_or_404(location_id)
        return services.update_location(location, get_json_body()).to_dict()

    def patch(self, location_id):
        location = get_location_or_404(location_id)
        return services.update_location(location, get_json_body(), partial=True).to_dict()

    def delete(self, location_id):
        services.delete_location(get_location_or_404(location_id))
        return "", 204


class EnrichResource(Resource):
    """Re-fetch coordinates + Wikipedia info for one location."""

    def post(self, location_id):
        return services.refresh_enrichment(get_location_or_404(location_id)).to_dict()


class EnrichMissingResource(Resource):
    """Enrich up to ?limit= locations that have no map/Wikipedia data yet.

    Synchronous and rate-limited (1 request/second to OpenStreetMap), so the
    limit is kept small; call it again until "checked" is 0.
    """

    def post(self):
        limit = int_arg("limit", 10, 1, 20)
        return services.enrich_missing(limit=limit)


class StatsResource(Resource):
    def get(self):
        return services.stats()


class ImportResource(Resource):
    """POST a JSON array (body) or a multipart file field named 'file'.

    ?mode=append (default) keeps existing data; ?mode=replace wipes it first.
    """

    method_decorators = [handle_service_errors]

    def post(self):
        mode = request.args.get("mode", "append")
        upload = request.files.get("file")
        if upload:
            try:
                items = json.load(upload)
            except ValueError:  # includes UnicodeDecodeError
                api_error(400, "Uploaded file is not valid JSON.")
        else:
            items = get_json_body()
        return services.import_locations(items, mode), 201


class ExportResource(Resource):
    def get(self):
        return [loc.to_dict() for loc in Location.query.order_by(Location.id).all()]


api.add_resource(LocationListResource, "/locations")
api.add_resource(LocationResource, "/locations/<int:location_id>")
api.add_resource(EnrichResource, "/locations/<int:location_id>/enrich")
api.add_resource(EnrichMissingResource, "/locations/enrich-missing")
api.add_resource(StatsResource, "/stats")
api.add_resource(ImportResource, "/locations/import")
api.add_resource(ExportResource, "/locations/export")
