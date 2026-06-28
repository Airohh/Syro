"""Non-régression extraction de texte (formats clés, sans dépendance lourde)."""

from app.services.file_extractor import detect_source_type, extract_text_from_bytes


class TestExtractTextFromBytes:
    def test_markdown_by_content_type(self):
        out = extract_text_from_bytes(b"# Titre\ncorps", "x.md", "text/markdown")
        assert "Titre" in out and "corps" in out

    def test_plain_text_by_extension(self):
        out = extract_text_from_bytes(b"hello world", "notes.txt", None)
        assert out == "hello world"

    def test_unknown_type_falls_back_to_utf8_decode(self):
        out = extract_text_from_bytes(b"raw bytes", "blob.bin", "application/x-thing")
        assert out == "raw bytes"

    def test_invalid_utf8_is_lenient(self):
        # errors="ignore" : pas d'exception sur des octets non décodables.
        out = extract_text_from_bytes(b"ok\xff\xfe", "x.txt", "text/plain")
        assert "ok" in out


class TestDetectSourceType:
    def test_uses_extension(self):
        assert detect_source_type("doc.PDF", None) == "pdf"

    def test_falls_back_to_content_type(self):
        assert detect_source_type("noext", "text/markdown") == "markdown"

    def test_unknown(self):
        assert detect_source_type("noext", None) == "unknown"
