import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


PLANS = {
    "30d": {"label": "30 Дней", "price": 149, "days": 30},
    "120d": {"label": "120 Дней", "price": 399, "days": 120},
    "forever": {"label": "Навсегда", "price": 799, "days": None},
    "hwid_reset": {"label": "Сброс HWID", "price": 100, "days": 0},
}


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    hwid = db.Column(db.String(128), nullable=True)
    subscription_until = db.Column(db.DateTime(timezone=True), nullable=True)
    lifetime = db.Column(db.Boolean, default=False, nullable=False)

    license_token = db.Column(
        db.String(64), unique=True, default=lambda: secrets.token_hex(24)
    )

    created_at = db.Column(db.DateTime(timezone=True), default=now)

    orders = db.relationship("Order", backref="user", lazy="dynamic")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        from flask import current_app

        return self.username in current_app.config["ADMIN_USERNAMES"]

    @property
    def is_active_subscriber(self):
        if self.lifetime:
            return True
        return bool(self.subscription_until and self.subscription_until > now())

    def extend_subscription(self, days):
        if days is None:
            self.lifetime = True
            self.subscription_until = None
            return
        base = self.subscription_until if (self.subscription_until and self.subscription_until > now()) else now()
        from datetime import timedelta

        self.subscription_until = base + timedelta(days=days)

    def regenerate_license_token(self):
        self.license_token = secrets.token_hex(24)


class Order(db.Model):
    """A purchase request. Payment is a stub: an admin manually marks it paid."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan = db.Column(db.String(32), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), default="pending")  # pending / paid / cancelled
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
