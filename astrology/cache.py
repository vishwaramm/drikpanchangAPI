"""In-memory result cache for astrology service responses."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from .utils import jsonable


def _freeze(value: Any) -> Any:
    value = jsonable(value)
    if isinstance(value, dict):
        return {str(key): _freeze(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_freeze(item) for item in value]
    if isinstance(value, set):
        return sorted(_freeze(item) for item in value)
    return value


def canonical_payload(payload: dict[str, Any]) -> str:
    frozen = _freeze(payload)
    return json.dumps(frozen, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


@dataclass
class AstrologyResultCache:
    maxsize: int = 512
    _store: OrderedDict[tuple[str, str], Any] = field(default_factory=OrderedDict)
    _lock: RLock = field(default_factory=RLock)

    def get(self, namespace: str, payload: dict[str, Any]) -> Any | None:
        key = (namespace, canonical_payload(payload))
        with self._lock:
            if key not in self._store:
                return None
            value = self._store.pop(key)
            self._store[key] = value
            return copy.deepcopy(value)

    def set(self, namespace: str, payload: dict[str, Any], result: Any) -> Any:
        key = (namespace, canonical_payload(payload))
        with self._lock:
            self._store[key] = copy.deepcopy(result)
            while len(self._store) > self.maxsize:
                self._store.popitem(last=False)
        return result

    def cached(self, namespace: str, payload: dict[str, Any], builder: Callable[[], Any]) -> Any:
        cached = self.get(namespace, payload)
        if cached is not None:
            return cached
        result = builder()
        self.set(namespace, payload, result)
        return result

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


@dataclass
class FileAstrologyResultCache:
    base_path: Path
    _lock: RLock = field(default_factory=RLock)

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _path_for(self, namespace: str, payload: dict[str, Any]) -> Path:
        canonical = canonical_payload(payload)
        digest = hashlib.sha256(f"{namespace}:{canonical}".encode("utf-8")).hexdigest()
        return self.base_path / f"{namespace}-{digest}.json"

    def get(self, namespace: str, payload: dict[str, Any]) -> Any | None:
        path = self._path_for(namespace, payload)
        if not path.exists():
            return None
        with self._lock, path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def set(self, namespace: str, payload: dict[str, Any], result: Any) -> Any:
        path = self._path_for(namespace, payload)
        tmp_path = path.with_suffix(".tmp")
        with self._lock, tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, default=jsonable)
        tmp_path.replace(path)
        return result

    def cached(self, namespace: str, payload: dict[str, Any], builder: Callable[[], Any]) -> Any:
        cached = self.get(namespace, payload)
        if cached is not None:
            return cached
        result = builder()
        self.set(namespace, payload, result)
        return result

    def clear(self) -> None:
        with self._lock:
            for path in self.base_path.glob("*.json"):
                path.unlink(missing_ok=True)
