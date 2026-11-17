from app.retriever import normalize


def test_normalize_preserves_spanish_negation():
    tokens = normalize("Hugo no desarrolló ni desplegó modelos")
    assert "no" in tokens
    assert "ni" in tokens


def test_normalize_preserves_english_negation():
    tokens = normalize("Hugo did not deploy models")
    assert "not" in tokens


def test_normalize_still_removes_common_filler_words():
    tokens = normalize("¿Qué hizo Hugo en Citibanamex?")
    assert "hizo" not in tokens
    assert "citibanamex" in tokens
