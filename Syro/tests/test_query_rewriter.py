"""Tests query rewriting (T2.1) — sans appel LLM réel."""

from unittest.mock import patch

from app.services.query_rewriter import _parse_rewrite_lines, rewrite


class TestParseRewriteLines:
    def test_strips_bullets_and_numbers(self):
        text = "1. reformulation A\n- reformulation B\n• reformulation C"
        assert _parse_rewrite_lines(text) == [
            "reformulation A",
            "reformulation B",
            "reformulation C",
        ]

    def test_ignores_short_lines(self):
        assert _parse_rewrite_lines("ok\n\n  x  ") == []


class TestRewrite:
    @patch("app.services.query_rewriter.settings")
    def test_disabled_returns_original_only(self, mock_settings):
        mock_settings.enable_query_rewriting = False
        mock_settings.query_rewrite_max_variants = 2

        assert rewrite("  Qu'est-ce que le RAG ?  ") == ["Qu'est-ce que le RAG ?"]

    @patch("app.services.query_rewriter._llm_rewrite_variants")
    @patch("app.services.query_rewriter.settings")
    def test_enabled_adds_deduped_variants(self, mock_settings, mock_llm):
        mock_settings.enable_query_rewriting = True
        mock_settings.query_rewrite_max_variants = 2

        mock_llm.return_value = [
            "définition retrieval augmented generation",
            "définition retrieval augmented generation",  # doublon
            "RAG architecture",
        ]

        result = rewrite("Qu'est-ce que le RAG ?", history=["message précédent"])

        assert result == [
            "Qu'est-ce que le RAG ?",
            "définition retrieval augmented generation",
            "RAG architecture",
        ]
        mock_llm.assert_called_once()

    @patch("app.services.query_rewriter._llm_rewrite_variants")
    @patch("app.services.query_rewriter.settings")
    def test_llm_failure_keeps_original(self, mock_settings, mock_llm):
        mock_settings.enable_query_rewriting = True
        mock_settings.query_rewrite_max_variants = 2
        mock_llm.return_value = []

        assert rewrite("question test") == ["question test"]

    @patch("app.services.query_rewriter._llm_rewrite_variants")
    @patch("app.services.query_rewriter.settings")
    def test_respects_max_variants(self, mock_settings, mock_llm):
        mock_settings.enable_query_rewriting = True
        mock_settings.query_rewrite_max_variants = 1

        mock_llm.return_value = ["variante A", "variante B", "variante C"]

        assert rewrite("q") == ["q", "variante A"]
