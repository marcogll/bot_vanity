from app.catalog_sync import parse_services_from_docs


def test_parse_services_from_docs_loads_catalog_and_promos() -> None:
    services = parse_services_from_docs()

    names = {item.name for item in services}

    assert "Manicure Vanity DELUXE" in names
    assert "Gelish (Manos)" in names
    assert "GELISH GLOW (Gelish Manos + Gelish Pies)" in names
    assert "PERFECT LOOK" in names
    assert any(item.source == "docs:knowledge_base" for item in services)
    assert any(item.source == "docs:promos" for item in services)
