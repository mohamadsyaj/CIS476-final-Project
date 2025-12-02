from datetime import datetime, timedelta
import secrets

from models import db


class UnmaskToken(db.Model):
    __tablename__ = 'unmask_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    item_id = db.Column(db.Integer, nullable=True)
    field = db.Column(db.String(128), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def issue(user_id: int, item_id: int | None = None, field: str | None = None, ttl_seconds: int = 30):
        # cleanup expired tokens first
        UnmaskToken.cleanup_expired()
        token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        ut = UnmaskToken(token=token, user_id=user_id, item_id=item_id, field=field, expires_at=now + timedelta(seconds=ttl_seconds))
        db.session.add(ut)
        db.session.commit()
        return ut

    @staticmethod
    def validate(token: str, user_id: int, item_id: int | None = None, field: str | None = None):
        # prune expired tokens first
        UnmaskToken.cleanup_expired()
        now = datetime.utcnow()
        ut = UnmaskToken.query.filter_by(token=token, user_id=user_id, used=False).first()
        if not ut:
            return None
        if ut.expires_at < now:
            return None
        # optional tighten: check item_id and field if present
        if item_id is not None and ut.item_id is not None and ut.item_id != item_id:
            return None
        if field is not None and ut.field and ut.field.lower() != field.lower():
            return None
        return ut

    @staticmethod
    def cleanup_expired():
        """Remove expired tokens from the database to keep table small."""
        now = datetime.utcnow()
        try:
            UnmaskToken.query.filter(UnmaskToken.expires_at < now).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
