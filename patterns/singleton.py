import threading
import time


class SingletonMeta(type):
    # Metaclass that ensures only ONE instance exists
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # Thread-safe creation of the singleton instance
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class UserSession(metaclass=SingletonMeta):
    """
    Simple session manager using the Singleton pattern.

    Stores:
    - current user_id
    - last activity time
    - inactivity timeout (auto lock)
    - small rate limiter for unmasking passwords
    """

    def __init__(self, inactivity_timeout: int = 60):
        self.user_id = None
        self.last_activity = None
        self.inactivity_timeout = inactivity_timeout
        self._lock = threading.RLock()

        # Rate limit settings (max 5 unmask operations per 60 seconds)
        self.unmask_quota = 5
        self.unmask_window = 60
        self._unmask_timestamps = []

    def set_user(self, user_id: int) -> None:
        # Log in a user
        with self._lock:
            self.user_id = user_id
            self.touch()

    def clear(self) -> None:
        # Log out the current user
        with self._lock:
            self.user_id = None
            self.last_activity = None

    def touch(self) -> None:
        # Update last activity time
        with self._lock:
            self.last_activity = time.time()

    def is_authenticated(self) -> bool:
        # Check if user ID exists and session isn't locked
        with self._lock:
            if self.user_id is None:
                return False
            if self.is_locked():
                return False
            return True

    def is_locked(self) -> bool:
        # Check if inactivity timeout has passed
        with self._lock:
            if self.last_activity is None:
                return True
            return (time.time() - self.last_activity) > self.inactivity_timeout

    def get_user_id(self):
        # Return user_id only if the session is active
        with self._lock:
            if self.is_authenticated():
                return self.user_id
            return None

    def can_unmask(self) -> bool:
        # Basic rate limiter for showing passwords
        with self._lock:
            now = time.time()
            # Keep only timestamps within the allowed window
            self._unmask_timestamps = [
                t for t in self._unmask_timestamps
                if now - t <= self.unmask_window
            ]
            return len(self._unmask_timestamps) < self.unmask_quota

    def record_unmask(self) -> None:
        # Record one unmask event
        with self._lock:
            self._unmask_timestamps.append(time.time())