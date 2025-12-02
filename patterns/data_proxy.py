class DataProxy:
    """Simple proxy that returns a human-readable masked preview string for a dict of fields."""

    SENSITIVE_SUBSTRINGS = ('password', 'card', 'cvv', 'ssn', 'social', 'passport', 'license')

    def _mask_value(self, v: str) -> str:
        s = '' if v is None else str(v)
        if len(s) <= 4:
            return '*' * len(s)
        return s[0] + '*' * (len(s) - 2) + s[-1]

    def mask_preview(self, data: dict) -> str:
        if not data:
            return ''
        parts = []
        for k, v in data.items():
            key = (k or '').lower()
            if any(sub in key for sub in self.SENSITIVE_SUBSTRINGS):
                parts.append(f"{k}: {self._mask_value(v)}")
            else:
                parts.append(f"{k}: {v}")
        return '; '.join(parts)


def mask_preview(data: dict) -> str:
    """Convenience function used by the app to get a masked preview string."""
    return DataProxy().mask_preview(data)


def mask_preview_dict(data: dict) -> dict:
    """Return a dict mapping each field name to its masked preview value.

    Sensitive-looking keys are masked; other keys return original values.
    """
    if not data:
        return {}
    dp = DataProxy()
    out = {}
    for k, v in data.items():
        key = (k or '').lower()
        if any(sub in key for sub in dp.SENSITIVE_SUBSTRINGS):
            out[k] = dp._mask_value(v)
        else:
            out[k] = v
    return out
