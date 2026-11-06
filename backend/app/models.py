from datetime import datetime, timezone

from .extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class Location(db.Model):
    __tablename__ = "locations"
    __table_args__ = (
        db.UniqueConstraint("name", "country", name="uq_location_name_country"),
        # The database itself refuses ratings outside 1-5, even if a bug in the
        # API let one through.
        db.CheckConstraint("rating IS NULL OR (rating BETWEEN 1 AND 5)", name="ck_location_rating_range"),
    )

    # --- fields the user edits ---
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(80), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    visited = db.Column(db.Boolean, nullable=False, default=False)
    rating = db.Column(db.SmallInteger, nullable=True)  # 1-5 stars, visited places only

    # --- fields filled in automatically (enrichment.py), editable as a fallback ---
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)  # short Wikipedia summary
    image_url = db.Column(db.String(500), nullable=True)  # Wikipedia thumbnail
    wiki_url = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "type": self.type,
            "visited": self.visited,
            "rating": self.rating,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "description": self.description,
            "image_url": self.image_url,
            "wiki_url": self.wiki_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Location {self.id} {self.name!r}>"
