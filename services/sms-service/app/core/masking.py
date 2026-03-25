"""Phone number masking utilities."""
import re

_MASK = "****"


def mask_phone(phone: str) -> str:
    """Mask a phone number: keep first 3 and last 4 digits, replace middle with ****."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return phone[:2] + _MASK if len(phone) > 2 else _MASK
    if phone.startswith("+"):
        # E.164: +8613800001234 → +86138****1234
        country_end = phone.index(digits[0])
        return phone[:country_end + 3] + _MASK + digits[-4:]
    return digits[:3] + _MASK + digits[-4:]
