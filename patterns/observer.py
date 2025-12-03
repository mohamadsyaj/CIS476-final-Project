from models.notification import Notification
from models import db


class BookingSubject:
    def __init__(self):
        # List of all observers (users who want updates)
        self.observers = []

    def attach(self, obs):
        # Add a new observer
        self.observers.append(obs)

    def status_changed(self, message):
        # Notify every observer about the update
        for o in self.observers:
            o.update(message)


class UserObserver:
    def __init__(self, user):
        # Store the user this observer represents
        self.user = user

    def update(self, message):
        # Create a notification record for this user
        try:
            note = Notification(user_id=self.user.id, content=message)
            db.session.add(note)
            db.session.commit()
        except Exception:
            # If something fails, undo the database changes
            db.session.rollback()
