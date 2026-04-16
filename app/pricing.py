from dataclasses import dataclass


@dataclass(frozen=True)
class PriceItem:
    name: str
    price: float
    minutes: int


@dataclass(frozen=True)
class PriceEstimate:
    items: tuple[PriceItem, ...]

    @property
    def total_price(self) -> float:
        return sum(item.price for item in self.items)

    @property
    def total_minutes(self) -> int:
        return sum(item.minutes for item in self.items)

    def to_prompt_hint(self) -> str:
        lines = [f"- {item.name}: ${item.price:.0f} MXN | {item.minutes} min" for item in self.items]
        lines.append(f"Total estimado: ${self.total_price:.0f} MXN | {self.total_minutes} min")
        return "\n".join(lines)


def estimate_from_message(message: str) -> PriceEstimate | None:
    normalized = message.casefold()
    items: list[PriceItem] = []

    service = _detect_base_service(normalized)
    if service:
        items.append(service)

    if any(word in normalized for word in ("retiro", "retirar", "quitar")):
        if any(word in normalized for word in ("pestaña", "lash")):
            items.append(PriceItem("Retiro de Pestañas (Otro Salón)", 200, 20))
        else:
            items.append(PriceItem("Retiro de Gel/Acrílico (Otro Salón)", 150, 20))

    nail_art = _detect_nail_art(normalized)
    if nail_art:
        items.append(nail_art)

    if any(word in normalized for word in ("vitamina", "capsula", "cápsula")):
        items.append(PriceItem("Cápsula de Vitamina", 110, 0))

    if not items:
        return None
    return PriceEstimate(tuple(items))


def _detect_base_service(normalized: str) -> PriceItem | None:
    if "gelish" in normalized and "pedi" not in normalized:
        return PriceItem("Gelish (Manos)", 350, 55)
    if "base rubber" in normalized:
        return PriceItem("Base Rubber", 750, 70)
    if "deluxe" in normalized and "pedi" in normalized:
        return PriceItem("Pedicure Vanity DELUXE", 850, 90)
    if "spa" in normalized and "pedi" in normalized:
        return PriceItem("Pedicure Vanity SPA", 800, 85)
    if "pedi classic" in normalized:
        return PriceItem("Pedi Classic + Gelish", 650, 60)
    if "deluxe" in normalized and any(word in normalized for word in ("manicure", "mani", "uña")):
        return PriceItem("Manicure Vanity DELUXE", 650, 90)
    if "spa" in normalized and any(word in normalized for word in ("manicure", "mani", "uña")):
        return PriceItem("Manicure Vanity SPA", 600, 85)
    if "classic" in normalized and any(word in normalized for word in ("manicure", "mani", "uña")):
        return PriceItem("Manicure Vanity CLASSIC", 550, 80)
    if any(word in normalized for word in ("acrílica", "acrilica", "acrilicas", "acrílicas")):
        if any(size in normalized for size in ("#5", "#6", "5", "6")):
            return PriceItem("Acrílicas Tamaño #5 - #6", 650, 120)
        if any(size in normalized for size in ("#3", "#4", "3", "4")):
            return PriceItem("Acrílicas Tamaño #3 - #4", 600, 105)
        return PriceItem("Acrílicas Tamaño #1 - #2", 550, 85)
    if "soft gel" in normalized:
        if any(size in normalized for size in ("#3", "#4", "3", "4")):
            return PriceItem("Soft Gel Tamaño #3 - #4", 550, 90)
        return PriceItem("Soft Gel Tamaño #1 - #2", 500, 85)
    return None


def _detect_nail_art(normalized: str) -> PriceItem | None:
    if "iconic" in normalized or "avanzado" in normalized or "cristal" in normalized:
        return PriceItem("Vanity Iconic (Avanzado)", 320, 30)
    if "art" in normalized or "medio" in normalized or "marmoleado" in normalized or "degradado" in normalized:
        return PriceItem("Vanity Art (Medio)", 160, 20)
    if "essence" in normalized or "básico" in normalized or "basico" in normalized:
        return PriceItem("Vanity Essence (Básico)", 110, 15)
    return None
