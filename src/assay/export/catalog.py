"""SQLite + Parquet catalog: the browsing surface for analysis and writing.

The catalog is DERIVED data: it is rebuilt from a VERIFIED run only, and
carries the run's hashes so any number in the paper traces back to bytes.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..ids import sha256_json


def build_catalog(run_dir: str | Path, out_path: str | Path) -> dict[str, Any]:
    import pandas as pd

    from ..evidence.store import RunStore

    store = RunStore(run_dir)
    manifest = store.read_manifest()
    trials = pd.DataFrame(list(store.iter_trials()))
    verdicts = pd.DataFrame(list(store.iter_verdicts()))
    privileged = pd.DataFrame(
        [
            {
                "trial_id": p["trial_id"],
                "turn_count": len(p.get("target_turn_audits", [])),
                "turn_audits_sha256": sha256_json(p.get("target_turn_audits", [])),
            }
            for p in store.iter_privileged()
        ]
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(out)
    trials.to_sql("trials", connection, if_exists="replace", index=False)
    verdicts.to_sql("verdicts", connection, if_exists="replace", index=False)
    if not privileged.empty:
        privileged.to_sql("privileged_index", connection, if_exists="replace", index=False)
    connection.executescript("""
    CREATE VIEW IF NOT EXISTS v_verdict_matrix AS
    SELECT trial_id, judge_id, value, parse_status FROM verdicts;
    CREATE VIEW IF NOT EXISTS v_harm_trials AS
    SELECT * FROM trials WHERE battery='harmful' AND status='completed';
    CREATE VIEW IF NOT EXISTS v_benign_trials AS
    SELECT * FROM trials WHERE battery='benign' AND status='completed';
    """)
    connection.commit()
    parquet_dir = out.parent / (out.stem + "_parquet")
    parquet_dir.mkdir(exist_ok=True)
    trials.to_parquet(parquet_dir / "trials.parquet", index=False)
    if not verdicts.empty:
        verdicts.to_parquet(parquet_dir / "verdicts.parquet", index=False)
    payload = {
        "run_id": manifest.get("run_id"),
        "config_sha256": manifest.get("config_sha256"),
        "trials": len(trials),
        "verdicts": len(verdicts),
        "catalog_sha256": sha256_json(
            {
                "trials": trials.to_dict("records")[:1],
                "counts": {"trials": len(trials), "verdicts": len(verdicts)},
            }
        ),
    }
    (out.parent / (out.stem + ".catalog.json")).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    connection.close()
    return payload


__all__ = ["build_catalog"]
