import threading
import time


class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class UserSession(metaclass=SingletonMeta):
    """Simple singleton session manager for the currently authenticated user.

    Holds `user_id` and `last_activity` timestamp and provides an inactivity
    timeout check (auto-lock). The timeout is configurable per instance.
    """

    def __init__(self, inactivity_timeout: int = 60):
        self.user_id = None
        self.last_activity = None
        self.inactivity_timeout = inactivity_timeout
        self._lock = threading.RLock()
        # unmask rate limiting: allow at most `unmask_quota` per `unmask_window` seconds
        self.unmask_quota = 5
        self.unmask_window = 60
        self._unmask_timestamps = []

    def set_user(self, user_id: int) -> None:
        with self._lock:
            self.user_id = user_id
            self.touch()

    def clear(self) -> None:
        with self._lock:
            self.user_id = None
            self.last_activity = None

    def touch(self) -> None:
        with self._lock:
            self.last_activity = time.time()

    def is_authenticated(self) -> bool:
        with self._lock:
            if self.user_id is None:
                return False
            if self.is_locked():
                return False
            return True

    def is_locked(self) -> bool:
        with self._lock:
            if self.last_activity is None:
                return True
            return (time.time() - self.last_activity) > self.inactivity_timeout

    def get_user_id(self):
        with self._lock:
            if self.is_authenticated():
                return self.user_id
            return None

    def can_unmask(self) -> bool:
        """Simple rate limiter for unmask/copy operations per singleton instance."""
        with self._lock:
            now = time.time()
            # drop old timestamps
            self._unmask_timestamps = [t for t in self._unmask_timestamps if now - t <= self.unmask_window]
            return len(self._unmask_timestamps) < self.unmask_quota

    def record_unmask(self) -> None:
        with self._lock:
            self._unmask_timestamps.append(time.time())
