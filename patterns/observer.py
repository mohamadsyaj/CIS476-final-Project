from models.notification import Notification
from models import db

class BookingSubject:
    def __init__(self):
        self.observers = []

    def attach(self, obs):
        self.observers.append(obs)

    def status_changed(self, message):
        for o in self.observers:
            o.update(message)

class UserObserver:
    def __init__(self, user):
        self.user = user

    def update(self, message):
        try:
            note = Notification(user_id=self.user.id, content=message)
            db.session.add(note)
            db.session.commit()
        except Exception:
            db.session.rollback()
