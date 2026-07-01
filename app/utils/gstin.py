"""GSTIN validation.

A GSTIN is 15 characters:
    2 digits   state code
    10 chars   PAN of the entity (5 letters, 4 digits, 1 letter)
    1 char     entity/registration number within the state (1-9 or A-Z)
    1 char     'Z' by default
    1 char     check digit (0-9 or A-Z), computed from the first 14

We validate the structural format and, optionally, the check digit.
"""

import re

# State code, PAN (AAAAA9999A), entity code, 'Z', check digit.
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

_CODE_POINTS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_MOD = len(_CODE_POINTS)  # 36


class InvalidGstinError(ValueError):
    """Raised when a GSTIN fails structural or checksum validation."""


def compute_check_digit(first_14: str) -> str:
    """Compute the 15th GSTIN check digit from the first 14 characters."""
    factor = 2
    total = 0
    for char in reversed(first_14):
        code = _CODE_POINTS.index(char)
        addend = factor * code
        factor = 1 if factor == 2 else 2
        addend = (addend // _MOD) + (addend % _MOD)
        total += addend
    return _CODE_POINTS[(_MOD - (total % _MOD)) % _MOD]


def normalize_gstin(gstin: str) -> str:
    """Trim and upper-case a GSTIN for consistent storage/comparison."""
    return gstin.strip().upper()


def validate_gstin(gstin: str, *, verify_checksum: bool = True) -> str:
    """Validate a GSTIN and return its normalized form.

    Raises InvalidGstinError if the format is wrong, or (when verify_checksum)
    if the check digit does not match.
    """
    normalized = normalize_gstin(gstin)
    if not GSTIN_REGEX.match(normalized):
        raise InvalidGstinError(
            "GSTIN must be 15 characters: 2-digit state code, 10-char PAN, "
            "entity code, 'Z', and a check digit."
        )
    if verify_checksum:
        expected = compute_check_digit(normalized[:14])
        if normalized[14] != expected:
            raise InvalidGstinError("GSTIN check digit is invalid.")
    return normalized
