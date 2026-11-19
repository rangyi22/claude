"""파일 기반 Job 상태 머신 (architecture.md §3).

status.json 에는 canonical 상태만 기록한다. photo progress event
(`photo_generating`, `photos_generated`, `photo_fallback`)는 상태 전이가 아니므로
이 모듈을 거치지 않고 on_stage callback 으로만 전달된다.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEQUENCE: tuple[str, ...] = (
    "created",
    "script_generated",
    "voice_generated",
    "transcribed",
    "subtitled",
    "final_rendered",
)
TERMINAL: frozenset[str] = frozenset({"qc_passed", "qc_failed", "failed"})
PROGRESS_EVENTS: frozenset[str] = frozenset({"photo_generating", "photos_generated", "photo_fallback"})

_ALLOWED: dict[str, frozenset[str]] = {
    "created": frozenset({"script_generated"}),
    "script_generated": frozenset({"voice_generated"}),
    "voice_generated": frozenset({"transcribed"}),
    "transcribed": frozenset({"subtitled"}),
    "subtitled": frozenset({"final_rendered"}),
    "final_rendered": frozenset({"qc_passed", "qc_failed"}),
}


def validate_transition(current: str | None, new: str) -> None:
    """허용되지 않은 전이면 ValueError."""
    if new in PROGRESS_EVENTS:
        raise ValueError(f"progress event {new!r} is not a status and must not be written to status.json")
    if current is None:
        if new != "created":
            raise ValueError(f"initial status must be 'created', got {new!r}")
        return
    if current in TERMINAL:
        raise ValueError(f"cannot transition from terminal status {current!r} to {new!r}")
    if new == "failed":
        return
    if new not in _ALLOWED.get(current, frozenset()):
        raise ValueError(f"invalid transition {current!r} -> {new!r}")


def new_job_id(now: datetime | None = None) -> str:
    """Job ID: sf_<YYYYMMDD>_<6 hex> (architecture.md §3.2). 날짜는 opening 과 같은 로컬 날짜."""
    now = now or datetime.now().astimezone()
    return f"sf_{now:%Y%m%d}_{secrets.token_hex(3)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_status(job_dir: Path) -> dict[str, Any]:
    path = job_dir / "status.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(job_dir: Path, status: str, **fields: Any) -> dict[str, Any]:
    """전이를 검증한 뒤 status.json 을 갱신한다."""
    doc = read_status(job_dir)
    validate_transition(doc.get("status"), status)
    now = _now_iso()
    if not doc:
        doc["started_at"] = now
    doc.update(fields)
    doc["status"] = status
    history = doc.setdefault("history", [])
    history.append({"status": status, "at": now})
    doc["updated_at"] = now
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "status.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
