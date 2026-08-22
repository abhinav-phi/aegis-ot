"""Object-store abstraction: deterministic local filesystem default + MinIO.

Keys are strictly validated (SEC-011): no traversal, no absolute paths,
restricted charset. `verify_hash` implements INV-016 verify-at-load.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import ValidationFailed

_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9/_.\-]{2,300}$")


def validate_key(key: str) -> str:
    if not _KEY_RE.match(key) or ".." in key:
        raise ValidationFailed(f"invalid_object_key: {key!r}")
    return key


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ObjectStore:
    def put(self, key: str, data: bytes, bucket: str = "aegis-raw") -> None: ...
    def get(self, key: str, bucket: str = "aegis-raw") -> bytes: ...
    def exists(self, key: str, bucket: str = "aegis-raw") -> bool: ...
    def delete(self, key: str, bucket: str = "aegis-raw") -> None: ...


class LocalObjectStore(ObjectStore):
    """Deterministic filesystem store rooted at AEGIS_OT_LOCAL_OBJECT_ROOT."""

    def __init__(self, root: str):
        self.root = Path(root)

    def _path(self, key: str, bucket: str) -> Path:
        validate_key(key)
        return self.root / bucket / key

    def put(self, key: str, data: bytes, bucket: str = "aegis-raw") -> None:
        p = self._path(key, bucket)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str, bucket: str = "aegis-raw") -> bytes:
        return self._path(key, bucket).read_bytes()

    def exists(self, key: str, bucket: str = "aegis-raw") -> bool:
        return self._path(key, bucket).exists()

    def delete(self, key: str, bucket: str = "aegis-raw") -> None:
        p = self._path(key, bucket)
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


class MinioObjectStore(ObjectStore):
    def __init__(self, endpoint: str, access: str, secret: str):
        from minio import Minio  # optional dependency

        secure = not endpoint.startswith("localhost")
        self.client = Minio(endpoint.replace("http://", "").replace("https://", ""),
                            access_key=access, secret_key=secret, secure=secure)

    def _bucket(self, bucket: str) -> str:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
        return bucket

    def put(self, key: str, data: bytes, bucket: str = "aegis-raw") -> None:
        import io

        b = self._bucket(bucket)
        self.client.put_object(b, key, io.BytesIO(data), length=len(data))

    def get(self, key: str, bucket: str = "aegis-raw") -> bytes:
        resp = self.client.get_object(self._bucket(bucket), key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def exists(self, key: str, bucket: str = "aegis-raw") -> bool:
        from minio.error import S3Error

        try:
            self.client.stat_object(self._bucket(bucket), key)
            return True
        except S3Error:
            return False

    def delete(self, key: str, bucket: str = "aegis-raw") -> None:
        self.client.remove_object(self._bucket(bucket), key)


def get_store() -> ObjectStore:
    s = get_settings()
    if s.object_store == "minio":
        return MinioObjectStore(s.minio_endpoint, s.minio_access_key, s.minio_secret_key)
    return LocalObjectStore(s.local_object_root)


def verify_hash(store: ObjectStore, key: str, expected_sha256: str,
                bucket: str = "aegis-raw") -> None:
    """INV-016: abort on any integrity mismatch before use."""
    actual = sha256_bytes(store.get(key, bucket))
    if actual != expected_sha256:
        raise ValidationFailed(
            f"integrity_mismatch: object {key} sha256={actual} expected={expected_sha256}"
        )
