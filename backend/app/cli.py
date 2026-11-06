import json

import click
from flask import current_app

from . import services
from .models import Location


def register_cli(app):
    @app.cli.command("seed-db")
    @click.option("--force", is_flag=True, help="Replace existing data with the seed file.")
    def seed_db(force):
        """Load seed/locations.json into an empty database."""
        if Location.query.count() and not force:
            click.echo("Database already has data; skipping seed (use --force to replace).")
            return
        with open(current_app.config["SEED_FILE"], encoding="utf-8") as fh:
            items = json.load(fh)
        result = services.import_locations(items, "replace" if force else "append")
        click.echo(f"Seeded {result['created']} locations.")

    @app.cli.command("enrich-db")
    @click.option("--limit", default=50, show_default=True, help="Max locations to process.")
    def enrich_db(limit):
        """Fetch map coordinates + Wikipedia info for locations that lack them."""
        if not current_app.config["ENRICHMENT_ENABLED"]:
            click.echo("Enrichment is disabled (ENRICHMENT_ENABLED=false).")
            return
        result = services.enrich_missing(limit=limit)
        click.echo(f"Checked {result['checked']} locations, enriched {result['updated']}.")
