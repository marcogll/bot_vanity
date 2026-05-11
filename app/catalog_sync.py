import csv
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import ServiceCatalog


SERVICE_LINE_RE = re.compile(
    r"^- \*\*(?P<name>.+?)\*\*(?: \*\((?P<meta>.+?)\)\*)? \| (?P<price>Desde \$[\d,]+|\$[\d,]+)(?: \| (?P<duration>[\d]+) min\.)?$"
)
DESCRIPTION_RE = re.compile(r"^\*Descripción:\* ?(?P<description>.+)$")


@dataclass
class ParsedService:
    slug: str
    name: str
    category: str
    service_type: str
    external_service_id: str | None
    description: str | None
    base_price: float
    purchase_price: float
    duration_minutes: int
    additional_time_minutes: int
    tax_percent: float
    source: str


def parse_services_from_docs() -> list[ParsedService]:
    settings = get_settings()
    docs_path = Path(settings.docs_path)
    services: list[ParsedService] = []
    services.extend(_parse_markdown_catalog(docs_path / "knowledge_base.md", source="docs:knowledge_base"))
    services.extend(_parse_markdown_catalog(docs_path / "promos.md", source="docs:promos"))
    return _dedupe_slugs(services)


def parse_services_from_fresha_csv(path: str | Path) -> list[ParsedService]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        services = [
            _parse_fresha_csv_row(row)
            for row in reader
            if (row.get("Nombre del servicio") or "").strip()
        ]
    return _dedupe_slugs(services)


async def sync_service_catalog_from_docs(
    db: AsyncSession,
    *,
    only_if_empty: bool = False,
) -> tuple[int, int]:
    existing_count = await db.scalar(select(ServiceCatalog.id).limit(1))
    if only_if_empty and existing_count is not None:
        return 0, 0

    created = 0
    updated = 0
    for item in parse_services_from_docs():
        result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.slug == item.slug))
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(
                ServiceCatalog(
                    slug=item.slug,
                    name=item.name,
                    category=item.category,
                    service_type=item.service_type,
                    external_service_id=item.external_service_id,
                    description=item.description,
                    base_price=item.base_price,
                    purchase_price=item.purchase_price,
                    duration_minutes=item.duration_minutes,
                    additional_time_minutes=item.additional_time_minutes,
                    tax_percent=item.tax_percent,
                    is_active=True,
                    source=item.source,
                )
            )
            created += 1
            continue
        if existing.source.startswith("docs:"):
            existing.name = item.name
            existing.category = item.category
            existing.service_type = item.service_type
            existing.external_service_id = item.external_service_id
            existing.description = item.description
            existing.base_price = item.base_price
            existing.purchase_price = item.purchase_price
            existing.duration_minutes = item.duration_minutes
            existing.additional_time_minutes = item.additional_time_minutes
            existing.tax_percent = item.tax_percent
            existing.is_active = True
            existing.source = item.source
            updated += 1
    await db.commit()
    return created, updated


async def sync_service_catalog_from_fresha_csv(
    db: AsyncSession,
    path: str | Path,
    *,
    only_if_exists: bool = True,
) -> tuple[int, int]:
    csv_path = Path(path)
    if only_if_exists and not csv_path.exists():
        return 0, 0

    created = 0
    updated = 0
    for item in parse_services_from_fresha_csv(csv_path):
        existing = await _find_existing_catalog_item(db, item)
        if existing is None:
            db.add(
                ServiceCatalog(
                    slug=item.slug,
                    name=item.name,
                    category=item.category,
                    service_type=item.service_type,
                    external_service_id=item.external_service_id,
                    description=item.description,
                    base_price=item.base_price,
                    purchase_price=item.purchase_price,
                    duration_minutes=item.duration_minutes,
                    additional_time_minutes=item.additional_time_minutes,
                    tax_percent=item.tax_percent,
                    is_active=True,
                    source=item.source,
                )
            )
            created += 1
            continue

        existing.slug = item.slug
        existing.name = item.name
        existing.category = item.category
        existing.service_type = item.service_type
        existing.external_service_id = item.external_service_id
        existing.description = item.description
        existing.base_price = item.base_price
        existing.purchase_price = item.purchase_price
        existing.duration_minutes = item.duration_minutes
        existing.additional_time_minutes = item.additional_time_minutes
        existing.tax_percent = item.tax_percent
        existing.is_active = True
        existing.source = item.source
        updated += 1
    await db.commit()
    return created, updated


def _parse_markdown_catalog(path: Path, *, source: str) -> list[ParsedService]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    items: list[ParsedService] = []
    current_category = "General"
    current_item: ParsedService | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            current_category = _normalize_category(line[3:])
            current_item = None
            continue
        if line.startswith("### "):
            current_category = _normalize_category(line[4:], parent=current_category)
            current_item = None
            continue

        match = SERVICE_LINE_RE.match(line)
        if match:
            name = match.group("name").strip()
            meta = (match.group("meta") or "").strip()
            price = _parse_price(match.group("price"))
            duration = int(match.group("duration") or "0")
            category = current_category
            description = None
            if meta and not name.endswith(f"({meta})"):
                name = f"{name} ({meta})"
            current_item = ParsedService(
                slug=_slugify(name),
                name=name,
                category=category,
                service_type=_infer_service_type(category, source, name),
                external_service_id=None,
                description=description,
                base_price=price,
                purchase_price=0.0,
                duration_minutes=duration,
                additional_time_minutes=0,
                tax_percent=0.0,
                source=source,
            )
            items.append(current_item)
            continue

        if current_item is not None:
            description_match = DESCRIPTION_RE.match(line)
            if description_match and not current_item.description:
                current_item.description = description_match.group("description").strip()

    return items


def _parse_fresha_csv_row(row: dict[str, str]) -> ParsedService:
    name = (row.get("Nombre del servicio") or "").strip()
    external_service_id = (row.get("ID del servicio") or "").strip() or None
    return ParsedService(
        slug=_slugify(name),
        name=name,
        category=(row.get("Nombre de la categoría") or "General").strip() or "General",
        service_type=_infer_fresha_service_type(
            row.get("Nombre de la categoría") or "",
            row.get("Tipo de servicio") or "",
            name,
        ),
        external_service_id=external_service_id,
        description=(row.get("Descripción") or "").strip() or None,
        base_price=_parse_decimal(row.get("Precio de compra") or "0"),
        purchase_price=0.0,
        duration_minutes=_parse_duration_minutes(row.get("Duración") or ""),
        additional_time_minutes=_parse_duration_minutes(row.get("Tiempo adicional") or ""),
        tax_percent=_parse_decimal(row.get("Impuestos") or "0"),
        source="fresha:csv",
    )


def _normalize_category(value: str, parent: str | None = None) -> str:
    cleaned = value.strip().strip("#").strip()
    cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()
    cleaned = re.sub(r"^[^\w]+", "", cleaned).strip()
    if parent and cleaned:
        return f"{parent} / {cleaned}"
    return cleaned or parent or "General"


def _parse_price(value: str) -> float:
    digits = re.sub(r"[^\d]", "", value)
    return float(digits or "0")


def _parse_decimal(value: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", value)
    try:
        return float(cleaned or "0")
    except ValueError:
        return 0.0


def _parse_duration_minutes(value: str) -> int:
    normalized = value.strip().casefold()
    if not normalized:
        return 0
    total = 0
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*h", normalized)
    minute_match = re.search(r"(\d+)\s*m", normalized)
    if hour_match:
        total += int(float(hour_match.group(1)) * 60)
    if minute_match:
        total += int(minute_match.group(1))
    if total:
        return total
    digits = re.sub(r"[^\d]", "", normalized)
    return int(digits or "0")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:120] or "service"


def _dedupe_slugs(items: list[ParsedService]) -> list[ParsedService]:
    counters: dict[str, int] = {}
    deduped: list[ParsedService] = []
    for item in items:
        base_slug = item.slug
        occurrence = counters.get(base_slug, 0) + 1
        counters[base_slug] = occurrence
        if occurrence > 1:
            item.slug = f"{base_slug}-{occurrence}"
        deduped.append(item)
    return deduped


def _infer_service_type(category: str, source: str, name: str) -> str:
    normalized_category = category.casefold()
    normalized_name = name.casefold()
    if source == "docs:promos":
        return "promo"
    if "nail art" in normalized_category or "vanity essence" in normalized_name or "vanity iconic" in normalized_name:
        return "nail_art"
    if "extras" in normalized_category or "complementos" in normalized_category:
        return "extra"
    if "paquetes" in normalized_category or "campana" in normalized_category or "campaña" in normalized_category:
        return "package"
    return "service"


def _infer_fresha_service_type(category: str, fresha_type: str, name: str) -> str:
    normalized_category = category.casefold()
    normalized_type = fresha_type.casefold()
    normalized_name = name.casefold()
    if "procedente de servicios" in normalized_type:
        return "package"
    if "promo" in normalized_category or "hello may" in normalized_category or "paquete" in normalized_name:
        return "package"
    if "retiro" in normalized_name or "extra" in normalized_category or "complemento" in normalized_category:
        return "extra"
    if "nail art" in normalized_name or "diseño" in normalized_name or "diseno" in normalized_name:
        return "nail_art"
    return "service"


async def _find_existing_catalog_item(db: AsyncSession, item: ParsedService) -> ServiceCatalog | None:
    conditions = [ServiceCatalog.slug == item.slug]
    if item.external_service_id:
        conditions.append(ServiceCatalog.external_service_id == item.external_service_id)
    result = await db.execute(select(ServiceCatalog).where(or_(*conditions)).limit(1))
    return result.scalar_one_or_none()
