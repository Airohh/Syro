"""Gate seuils retrieval (T1.4) — compare report.json aux seuils configurables.

Usage:
    python evaluation/validate_retrieval_thresholds.py
    python evaluation/validate_retrieval_thresholds.py --report evaluation/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_REPORT = EVAL_DIR / "report.json"
DEFAULT_THRESHOLDS = EVAL_DIR / "retrieval_thresholds.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_thresholds(report: dict, thresholds: dict) -> list[str]:
    """Retourne la liste des violations (vide = gate OK)."""
    errors: list[str] = []
    metrics = report.get("retrieval_metrics") or report.get("retrieval") or {}

    for key, spec in thresholds.items():
        if not isinstance(spec, dict):
            continue
        minimum = spec.get("min")
        if minimum is None:
            continue
        value = metrics.get(key)
        if value is None:
            errors.append(f"métrique absente: {key}")
            continue
        if float(value) < float(minimum):
            errors.append(f"{key}={value:.4f} < seuil {minimum}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate qualité retrieval (T1.4)")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--skip-missing", action="store_true", help="Exit 0 si report absent")
    args = parser.parse_args()

    if not args.report.exists():
        if args.skip_missing:
            print(f"Report absent ({args.report}) — gate ignoré.")
            return
        print(f"Report introuvable: {args.report}")
        sys.exit(1)

    if not args.thresholds.exists():
        print(f"Seuils introuvables: {args.thresholds}")
        sys.exit(1)

    report = load_json(args.report)
    thresholds = load_json(args.thresholds)
    errors = check_thresholds(report, thresholds)

    if errors:
        print(f"Gate retrieval ÉCHEC ({len(errors)} violations):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("Gate retrieval OK — tous les seuils respectés.")


if __name__ == "__main__":
    main()
