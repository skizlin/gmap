"""Persist internal pricing snapshots (per-environment data under data/internal_feed/)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def save_snapshot(base_dir: Path, domain_event_id: str, domain_market_id: str, payload: dict) -> Path:
    """Write JSON snapshot; returns path written."""
    base_dir.mkdir(parents=True, exist_ok=True)
    safe_e = str(domain_event_id).replace("/", "_").replace("\\", "_")
    safe_m = str(domain_market_id).replace("/", "_").replace("\\", "_")
    path = base_dir / safe_e / f"{safe_m}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        **payload,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return path
