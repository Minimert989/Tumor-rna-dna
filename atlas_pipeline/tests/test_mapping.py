from cancer_atlas.mapping import map_name


def test_map_name_exact_and_fuzzy():
    mapping = {"small cell lung cancer": "SCLC", "non small cell lung cancer": "NSCLC"}
    choices = list(mapping)
    assert map_name("Small-cell lung cancer", mapping, choices, 90)[0] == "SCLC"
    assert map_name("unrelated infection", mapping, choices, 90)[0] is None
