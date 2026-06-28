"""Non-régression cadrage SSE : un fragment multi-ligne reste un évènement valide."""

from app.routers.chat import _sse


def test_sse_single_line():
    assert _sse("hello") == "data: hello\n\n"


def test_sse_multiline_prefixes_each_line():
    # Spec SSE : un champ `data:` par ligne, sinon le `\n` interne coupe l'event.
    out = _sse("line1\nline2")
    assert out == "data: line1\ndata: line2\n\n"
    # L'évènement se termine bien par une ligne vide unique.
    assert out.endswith("\n\n")
    assert "line2\n\n" in out


def test_sse_empty_chunk_still_framed():
    assert _sse("") == "data: \n\n"
