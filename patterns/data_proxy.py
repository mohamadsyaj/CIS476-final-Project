class DataProxy:

    # Words that indicate the field is sensitive and should be masked
    SENSITIVE_SUBSTRINGS = ('password', 'card', 'cvv', 'ssn', 'social', 'passport', 'license')

    def _mask_value(self, v: str) -> str:
        # Convert value to string safely
        s = '' if v is None else str(v)

        # If value is short, mask the whole thing
        if len(s) <= 4:
            return '*' * len(s)

        # Otherwise keep first and last character visible
        return s[0] + '*' * (len(s) - 2) + s[-1]

    def mask_preview(self, data: dict) -> str:
        # Return empty string for empty input
        if not data:
            return ''

        parts = []
        for k, v in data.items():
            key = (k or '').lower()

            # If the key looks sensitive, mask the value
            if any(sub in key for sub in self.SENSITIVE_SUBSTRINGS):
                parts.append(f"{k}: {self._mask_value(v)}")
            else:
                parts.append(f"{k}: {v}")

        # Join everything into a single readable string
        return '; '.join(parts)


def mask_preview(data: dict) -> str:
    # Helper wrapper for string preview
    return DataProxy().mask_preview(data)


def mask_preview_dict(data: dict) -> dict:
    # Return empty dict if nothing is provided
    if not data:
        return {}

    dp = DataProxy()
    out = {}

    for k, v in data.items():
        key = (k or '').lower()

        # Mask only sensitive keys
        if any(sub in key for sub in dp.SENSITIVE_SUBSTRINGS):
            out[k] = dp._mask_value(v)
        else:
            out[k] = v

    return out
