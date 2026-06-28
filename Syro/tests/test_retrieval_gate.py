"""Tests gate seuils retrieval (T1.4)."""

import json
from pathlib import Path

from evaluation.validate_retrieval_thresholds import check_thresholds


def test_gate_passes_above_thresholds():
    report = {"retrieval_metrics": {"recall_at_10": 0.6, "ndcg_at_10": 0.5, "mrr": 0.4}}
    thresholds = {
        "recall_at_10": {"min": 0.45},
        "ndcg_at_10": {"min": 0.35},
        "mrr": {"min": 0.30},
    }
    assert check_thresholds(report, thresholds) == []


def test_gate_fails_below_threshold():
    report = {"retrieval_metrics": {"recall_at_10": 0.2}}
    thresholds = {"recall_at_10": {"min": 0.45}}
    errors = check_thresholds(report, thresholds)
    assert len(errors) == 1
    assert "recall_at_10" in errors[0]


def test_thresholds_file_valid_json():
    path = Path(__file__).resolve().parent.parent / "evaluation" / "retrieval_thresholds.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "recall_at_10" in data
    assert "min" in data["recall_at_10"]
