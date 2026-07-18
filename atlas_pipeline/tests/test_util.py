from cancer_atlas.util import normalize_text, stable_id


def test_normalize_text():
    assert normalize_text("Non–Small Cell Lung Cancer") == "non small cell lung cancer"


def test_stable_id_is_stable():
    assert stable_id("a", 1) == stable_id("a", 1)
    assert stable_id("a", 1) != stable_id("a", 2)
