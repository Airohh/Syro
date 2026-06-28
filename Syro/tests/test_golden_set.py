"""T1.4 (gate déterministe) : le golden set reste intègre à chaque merge."""

import json

from evaluation import validate_golden_set as vgs


def _load():
    dataset = json.loads(vgs.DATASET_PATH.read_text(encoding="utf-8"))
    return dataset, vgs.corpus_filenames()


def test_golden_set_is_valid():
    dataset, corpus = _load()
    errors = vgs.validate_dataset(dataset, corpus)
    assert errors == [], "Golden set invalide:\n" + "\n".join(errors)


def test_golden_set_meets_minimums():
    dataset, _ = _load()
    assert len(dataset) >= vgs.MIN_PAIRS
    buckets = {d["intent"] for d in dataset if d.get("intent")}
    assert len(buckets) >= vgs.MIN_BUCKETS


class TestValidatorCatchesProblems:
    def test_flags_missing_corpus_doc(self):
        bad = [{"question": "q", "ground_truth": "a", "domain": "tech",
                "intent": "factual_lookup", "relevant_doc_ids": ["does-not-exist.md"]}]
        errors = vgs.validate_dataset(bad, {"01-rag-fundamentals.md"})
        assert any("absent du corpus" in e for e in errors)

    def test_flags_oob_with_docs(self):
        bad = [{"question": "q", "ground_truth": "a", "domain": "tech",
                "intent": "out_of_corpus", "relevant_doc_ids": ["01-rag-fundamentals.md"]}]
        errors = vgs.validate_dataset(bad, {"01-rag-fundamentals.md"})
        assert any("out_of_corpus" in e for e in errors)

    def test_flags_duplicate_question(self):
        bad = [
            {"question": "Même Q", "ground_truth": "a", "domain": "tech"},
            {"question": "même q", "ground_truth": "b", "domain": "mlops"},
        ]
        errors = vgs.validate_dataset(bad, set())
        assert any("dupliquée" in e for e in errors)

    def test_flags_missing_intent(self):
        bad = [
            {
                "question": "q",
                "ground_truth": "a",
                "domain": "tech",
                "relevant_doc_ids": ["01-rag-fundamentals.md"],
            }
        ]
        errors = vgs.validate_dataset(bad, {"01-rag-fundamentals.md"})
        assert any("intent manquant" in e for e in errors)
