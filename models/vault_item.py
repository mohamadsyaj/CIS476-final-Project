from . import db

class VaultItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    item_type = db.Column(db.String(100))
    title = db.Column(db.String(255))
    encrypted_data = db.Column(db.Text)
