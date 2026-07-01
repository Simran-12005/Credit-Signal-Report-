"""API-key generation and hashing.

A key looks like  csr_<43 url-safe base64 chars>. We store only its SHA-256 hash;
the plaintext is shown once at creation. Lookup hashes the presented key and matches.
"""

import hashlib
import secrets

KEY_PREFIX = "csr_"
PREFIX_STORED_LEN = 12  # how many leading chars of the key we keep for identification


def generate_api_key() -> str:
    """Return a new plaintext API key. Show once, never stored in plaintext."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """SHA-256 hex digest of a key, used for storage and lookup."""
    return hashlib.sha256(key.encode()).hexdigest()


def key_prefix(key: str) -> str:
    """Leading chars of a key, stored to identify it in listings."""
    return key[:PREFIX_STORED_LEN]
