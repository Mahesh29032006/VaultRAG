import json
import os
import pickle
from pathlib import Path
from typing import Any


def ensure_dirs(paths: list[str]) -> None:
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def atomic_write_bytes(path: str, data: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f"{target.suffix}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except Exception:
        if tmp.exists():
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def atomic_write_json(path: str, obj: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f"{target.suffix}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except Exception:
        if tmp.exists():
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def atomic_write_pickle(path: str, obj: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f"{target.suffix}.tmp")
    try:
        with open(tmp, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except Exception:
        if tmp.exists():
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def read_json(path: str, default: Any = None) -> Any:
    target = Path(path)
    if not target.is_file():
        return default
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def read_pickle(path: str, default: Any = None) -> Any:
    target = Path(path)
    if not target.is_file():
        return default
    with open(target, "rb") as f:
        return pickle.load(f)
