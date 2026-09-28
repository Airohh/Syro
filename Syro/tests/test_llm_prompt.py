"""Prompt RAG et préfixes d'embedding."""

from unittest.mock import patch

from app.services import llm
from app.services.domain_detector import classify_text, detect_domain


class TestPrefixes:
    @patch("app.services.llm.settings")
    def test_nomic_gets_task_prefixes(self, s):
        s.embeddings_model = "nomic-embed-text"
        s.embedding_query_prefix = None
        s.embedding_document_prefix = None
        assert llm._prefixes() == ("search_query: ", "search_document: ")

    @patch("app.services.llm.settings")
    def test_openai_has_none_and_override_wins(self, s):
        s.embeddings_model = "text-embedding-3-small"
        s.embedding_query_prefix = None
        s.embedding_document_prefix = "doc: "
        assert llm._prefixes() == ("", "doc: ")


class TestBuildMessages:
    def test_sources_before_question_with_filenames_and_history(self):
        chunks = [{"text": "Qdrant est une base vectorielle.", "metadata": {"filename": "06-qdrant.md"}}]
        history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Salut"},
        ]
        messages = llm.build_messages("C'est quoi Qdrant ?", chunks, "tech", history)

        assert "SyroTech" in messages[0].content
        assert "UNIQUEMENT" in messages[0].content
        assert [type(m).__name__ for m in messages[1:3]] == ["HumanMessage", "AIMessage"]
        last = messages[-1].content
        assert last.index("<sources>") < last.index("Question :")
        assert "[Source 1] (06-qdrant.md)" in last


class TestDomainDetector:
    def test_word_boundaries(self):
        # « tf » ne doit plus matcher « pdf », ni « art » matcher « start ».
        assert classify_text("start a pdf export")["domain"] == "general"

    def test_french_keywords_without_accents(self):
        assert detect_domain("Comment surveiller le drift avec MLflow ?") == "mlops"
        assert classify_text("Le médecin prescrit un traitement au patient")["domain"] == "medical"
