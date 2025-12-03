import secrets
import string
from typing import Optional


class PasswordBuilder:
    def __init__(self):
        # Default password settings
        self.length = 16
        self.use_upper = True
        self.use_lower = True
        self.use_digits = True
        self.use_symbols = False

    def set_length(self, length: int) -> 'PasswordBuilder':
        # Make sure length isn't too small
        self.length = max(4, int(length))
        return self

    def with_upper(self, enable: bool = True) -> 'PasswordBuilder':
        # Turn uppercase letters on/off
        self.use_upper = bool(enable)
        return self

    def with_lower(self, enable: bool = True) -> 'PasswordBuilder':
        # Turn lowercase letters on/off
        self.use_lower = bool(enable)
        return self

    def with_digits(self, enable: bool = True) -> 'PasswordBuilder':
        # Turn digits on/off
        self.use_digits = bool(enable)
        return self

    def with_symbols(self, enable: bool = True) -> 'PasswordBuilder':
        # Turn special characters on/off
        self.use_symbols = bool(enable)
        return self

    def build(self) -> str:
        # Build the character pool based on chosen options
        pool = ''
        if self.use_lower:
            pool += string.ascii_lowercase
        if self.use_upper:
            pool += string.ascii_uppercase
        if self.use_digits:
            pool += string.digits
        if self.use_symbols:
            pool += '!@#$%^&*()-_=+[]{};:,.<>?'

        # If everything is disabled, fall back to letters + digits
        if not pool:
            pool = string.ascii_letters + string.digits

        # Make sure we include at least one character from each enabled type
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

        # Add one guaranteed character from each class
        for cls in classes:
            password_chars.append(secrets.choice(cls))

        # Fill the rest randomly until we reach the desired length
        while len(password_chars) < self.length:
            password_chars.append(secrets.choice(pool))

        # Shuffle so the guaranteed chars aren't always in front
        secrets.SystemRandom().shuffle(password_chars)

        return ''.join(password_chars[: self.length])


def generate_password(length: Optional[int] = 16, upper: bool = True, lower: bool = True, digits: bool = True, symbols: bool = False) -> str:
    # Simple helper function to build a password with one call
    return (
        PasswordBuilder()
        .set_length(length)
        .with_upper(upper)
        .with_lower(lower)
        .with_digits(digits)
        .with_symbols(symbols)
        .build()
    )
