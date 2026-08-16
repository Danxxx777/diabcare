"""Hash de contraseñas (bcrypt). Nunca se guarda la clave en claro ni cifrada reversible.

Compat: hashes legacy SHA-256 (64 hex) se aceptan una vez y se migran a bcrypt.
"""
from __future__ import annotations

import hashlib
import re

import bcrypt

_LEGACY_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def hash_password(password: str) -> str:
    raw = (password or "").encode("utf-8")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def _es_legacy_sha256(stored: str) -> bool:
    return bool(_LEGACY_SHA256.match((stored or "").strip().lower()))


def verificar_password(password: str, stored_hash: str) -> bool:
    stored = (stored_hash or "").strip()
    if not stored:
        return False
    pwd = password or ""
    if stored.startswith("$2"):
        try:
            return bcrypt.checkpw(pwd.encode("utf-8"), stored.encode("ascii"))
        except (ValueError, TypeError):
            return False
    if _es_legacy_sha256(stored):
        return hashlib.sha256(pwd.encode("utf-8")).hexdigest() == stored.lower()
    return False


def necesita_rehash(stored_hash: str) -> bool:
    """True si conviene reescribir el hash (legacy SHA-256 u otro formato viejo)."""
    stored = (stored_hash or "").strip()
    if not stored:
        return True
    return not stored.startswith("$2")
