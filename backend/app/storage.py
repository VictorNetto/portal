"""Object storage for attachments (SPEC §5.1), behind a small interface.

Two backends, chosen by `STORAGE_BACKEND`:
  local — files on a Docker volume. Default; needs no extra image/service.
  s3    — any S3-compatible server (MinIO per the spec) via the `minio` SDK.

Callers only ever use put/open/delete with an opaque key, so swapping the
backend never touches the endpoints. Files are never exposed directly: the
API proxies every read (so authentication and auditing always apply).
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Protocol

from app.config import settings

CHUNK = 1024 * 256


class Storage(Protocol):
    def put(self, key: str, fileobj: BinaryIO, size: int, content_type: str) -> None: ...
    def open(self, key: str) -> Iterator[bytes]: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Keys are generated server-side, but never trust a path blindly.
        if self.root not in path.parents:
            raise ValueError("invalid storage key")
        return path

    def put(self, key: str, fileobj: BinaryIO, size: int, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as out:
            shutil.copyfileobj(fileobj, out, CHUNK)

    def open(self, key: str) -> Iterator[bytes]:
        with self._path(key).open("rb") as f:
            while chunk := f.read(CHUNK):
                yield chunk

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self) -> None:
        from minio import Minio  # imported lazily: only needed for this backend

        self.bucket = settings.minio_bucket
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ready = False

    def _ensure_bucket(self) -> None:
        if not self._ready:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
            self._ready = True

    def put(self, key: str, fileobj: BinaryIO, size: int, content_type: str) -> None:
        self._ensure_bucket()
        self.client.put_object(self.bucket, key, fileobj, length=size, content_type=content_type)

    def open(self, key: str) -> Iterator[bytes]:
        resp = self.client.get_object(self.bucket, key)
        try:
            yield from resp.stream(CHUNK)
        finally:
            resp.close()
            resp.release_conn()

    def delete(self, key: str) -> None:
        self.client.remove_object(self.bucket, key)


@lru_cache
def get_storage() -> Storage:
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(settings.storage_local_path)
