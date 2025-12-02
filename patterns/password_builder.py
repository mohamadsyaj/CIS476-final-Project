import secrets
import string
from typing import Optional


class PasswordBuilder:
    def __init__(self):
        self.length = 16
        self.use_upper = True
        self.use_lower = True
        self.use_digits = True
        self.use_symbols = False

    def set_length(self, length: int) -> 'PasswordBuilder':
        self.length = max(4, int(length))
        return self

    def with_upper(self, enable: bool = True) -> 'PasswordBuilder':
        self.use_upper = bool(enable)
        return self

    def with_lower(self, enable: bool = True) -> 'PasswordBuilder':
        self.use_lower = bool(enable)
        return self

    def with_digits(self, enable: bool = True) -> 'PasswordBuilder':
        self.use_digits = bool(enable)
        return self

    def with_symbols(self, enable: bool = True) -> 'PasswordBuilder':
        self.use_symbols = bool(enable)
        return self

    def build(self) -> str:
        pool = ''
        if self.use_lower:
            pool += string.ascii_lowercase
        if self.use_upper:
            pool += string.ascii_uppercase
        if self.use_digits:
            pool += string.digits
        if self.use_symbols:
            pool += '!@#$%^&*()-_=+[]{};:,.<>?'

        if not pool:
            pool = string.ascii_letters + string.digits

        # Ensure at least one of each selected class is present when possible
        password_chars = []
        classes = []
        if self.use_lower:
            classes.append(string.ascii_lowercase)
        if self.use_upper:
            classes.append(string.ascii_uppercase)
        if self.use_digits:
            classes.append(string.digits)
        if self.use_symbols:
            classes.append('!@#$%^&*()-_=+[]{};:,.<>?')

        for cls in classes:
            password_chars.append(secrets.choice(cls))

        while len(password_chars) < self.length:
            password_chars.append(secrets.choice(pool))

        # Shuffle securely
        secrets.SystemRandom().shuffle(password_chars)
        return ''.join(password_chars[: self.length])


def generate_password(length: Optional[int] = 16, upper: bool = True, lower: bool = True, digits: bool = True, symbols: bool = False) -> str:
    return PasswordBuilder().set_length(length).with_upper(upper).with_lower(lower).with_digits(digits).with_symbols(symbols).build()
