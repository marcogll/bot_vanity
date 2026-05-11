from app.catalog_sync import parse_services_from_fresha_csv


def test_parse_services_from_fresha_csv_uses_fresha_names_prices_and_duration(tmp_path) -> None:
    csv_path = tmp_path / "export_service_list_2026-05-11.csv"
    csv_path.write_text(
        "\n".join(
            [
                '"Nombre del servicio","Precio de compra","Duración","Tiempo adicional","Impuestos","Descripción","Nombre de la categoría","Tipo de servicio","Recurso","Reserva online","Disponible para","Ventas de cupones","Comisiones","ID del servicio","SKU"',
                '"GELISH GLOW (gelish manos y pies)","700.00","1h 35m","","Procedente de servicios","Paquete de gel en manos y pies","💗 HELLO MAY 💗","Procedente de servicios","","Activo","Todos","Desactivado","","",""',
            ]
        ),
        encoding="utf-8",
    )

    services = parse_services_from_fresha_csv(csv_path)
    by_name = {item.name: item for item in services}

    gelish_glow = by_name["GELISH GLOW (gelish manos y pies)"]

    assert gelish_glow.source == "fresha:csv"
    assert gelish_glow.category == "💗 HELLO MAY 💗"
    assert gelish_glow.service_type == "package"
    assert gelish_glow.base_price == 700
    assert gelish_glow.duration_minutes == 95
    assert "GELISH GLOW (Gelish Manos + Gelish Pies)" not in by_name
