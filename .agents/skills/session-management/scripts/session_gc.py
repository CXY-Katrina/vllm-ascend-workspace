#!/usr/bin/env python3
"""Conservative local GC for stale VAWS session metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
LIB_DIR = ROOT / ".agents" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from vaws_session_state import load_index, load_session_lookup, release_all_session_leases  # noqa: E402


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="show stale lease releases without mutating state (default)",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="actually release leases for removed or missing session metadata",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dry_run = not args.apply
    try:
        index = load_index(ROOT)
        released: list[str] = []
        checked: list[dict[str, Any]] = []
        for sid in sorted(index.get("sessions", {})):
            try:
                lookup = load_session_lookup(session_id=sid, repo_root=ROOT)
                session = lookup.session
            except Exception as exc:  # noqa: BLE001
                checked.append({"session_id": sid, "status": "missing-state", "error": str(exc)})
                if not dry_run:
                    release_all_session_leases(repo_root=ROOT, session_id=sid)
                released.append(sid)
                continue
            if session.get("status") == "removed":
                if not dry_run:
                    release_all_session_leases(repo_root=lookup.state_repo_root, session_id=sid)
                released.append(sid)
            checked.append({"session_id": sid, "status": session.get("status")})
        print_json(
            {
                "status": "ok",
                "dry_run": dry_run,
                "checked": checked,
                "released_lease_sessions": [] if dry_run else sorted(set(released)),
                "would_release_lease_sessions": sorted(set(released)) if dry_run else [],
            }
        )
        return 0
    except Exception as exc:
        print_json({"status": "failed", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
