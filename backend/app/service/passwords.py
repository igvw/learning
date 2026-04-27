import base64
import hashlib
import hmac

from pwdlib import PasswordHash, exceptions as pwdlib_exceptions

from .errors import ValidationError


_PASSWORD_HASHER = PasswordHash.recommended()
_LEGACY_SCRYPT_PREFIX = "scrypt"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_LENGTH = 64


def hash_password(password: str) -> str:
    cleaned_password = _clean_password(password, validate_length=True)
    return _PASSWORD_HASHER.hash(cleaned_password)


def verify_password_and_update(password: str, stored_hash: str | None) -> tuple[bool, str | None]:
    if not stored_hash:
        return False, None

    cleaned_password = _clean_password(password, validate_length=False)
    if _is_legacy_scrypt_hash(stored_hash):
        if not _verify_legacy_scrypt_password(cleaned_password, stored_hash):
            return False, None
        return True, hash_password(cleaned_password)

    try:
        return _PASSWORD_HASHER.verify_and_update(cleaned_password, stored_hash)
    except (pwdlib_exceptions.UnknownHashError, ValueError):
        return False, None


def _clean_password(password: str, *, validate_length: bool) -> str:
    cleaned_password = password.strip()
    if validate_length and len(cleaned_password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    return cleaned_password


def _is_legacy_scrypt_hash(stored_hash: str) -> bool:
    return stored_hash.startswith(f"{_LEGACY_SCRYPT_PREFIX}:")


def _verify_legacy_scrypt_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, raw_n, raw_r, raw_p, salt_b64, digest_b64 = stored_hash.split(":", 5)
        if algorithm != _LEGACY_SCRYPT_PREFIX:
            return False
        salt = base64.b64decode(salt_b64)
        expected_digest = base64.b64decode(digest_b64)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(raw_n),
            r=int(raw_r),
            p=int(raw_p),
            dklen=len(expected_digest),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected_digest)
