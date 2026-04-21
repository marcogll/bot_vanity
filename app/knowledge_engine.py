from datetime import datetime
from functools import lru_cache
import logging
from pathlib import Path

from app.config import get_settings


logger = logging.getLogger("vanessa.knowledge")


class KnowledgeEngine:
    REQUIRED_DOCS = (
        "system_prompt.md",
        "knowledge_base.md",
        "promos.md",
        "db.md",
    )
    EVOLUTION_DOC_CANDIDATES = (
        "create_evolution_bot.md",
        "create_evolution_bot_instructions.md",
    )

    def __init__(self, docs_path: str) -> None:
        self.docs_path = Path(docs_path)
        self._documents: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        loaded: dict[str, str] = {}
        missing: list[str] = []
        for filename in self.REQUIRED_DOCS:
            path = self.docs_path / filename
            if not path.exists():
                missing.append(str(path))
                continue
            loaded[filename] = path.read_text(encoding="utf-8")
        evolution_doc = self._load_first_existing(self.EVOLUTION_DOC_CANDIDATES)
        if evolution_doc is None:
            missing.append(
                " or ".join(str(self.docs_path / name) for name in self.EVOLUTION_DOC_CANDIDATES)
            )
        else:
            filename, content = evolution_doc
            loaded[filename] = content

        if missing:
            logger.warning("Missing knowledge documents: %s", ", ".join(missing))

        self._documents = loaded

    def _load_first_existing(self, filenames: tuple[str, ...]) -> tuple[str, str] | None:
        for filename in filenames:
            path = self.docs_path / filename
            if path.exists():
                return filename, path.read_text(encoding="utf-8")
        return None

    def build_system_prompt(
        self,
        current_datetime: datetime,
        memory_context: str | None = None,
    ) -> str:
        settings = get_settings()
        placeholders = {
            "{booking_url}": settings.booking_url,
            "{ios_app_store_url}": settings.ios_app_store_url,
            "{android_play_store_url}": settings.android_play_store_url,
            "{payment_url}": settings.payment_url,
        }
        docs_block = "\n\n".join(
            f"--- {filename} ---\n{self._replace_placeholders(content, placeholders)}"
            for filename, content in self._documents.items()
        )
        memory = memory_context or "Sin contexto previo disponible."

        return f"""
Fecha y hora actual del sistema: {current_datetime.isoformat()}
Liga oficial de agendamiento Fresha: {get_settings().booking_url}
Liga App Store (iOS): {get_settings().ios_app_store_url}
Liga Play Store (Android): {get_settings().android_play_store_url}
Liga de pago/anticipo: {get_settings().payment_url}

Contexto previo del cliente:
{memory}

Reglas operativas obligatorias:
- No proporciones la liga de agendamiento hasta haber preguntado por Retiro y Nail Art cuando el servicio sea de uñas.
- Si el cliente busca pestañas, pregunta por Retiro de Pestañas antes de cotizar o cerrar.
- Usa solo precios, duraciones y promociones presentes en los documentos.
- Valida promociones temporales contra la fecha actual antes de ofrecerlas.
- Si falta información para cotizar, pregunta una cosa concreta antes de avanzar.
- Usa la base documental como referencia interna, no como texto para volcar completo al cliente.
- No enumeres catálogos completos, listas largas de servicios, ni promociones no relacionadas con lo que la clienta pidió.
- Responde con la mínima información útil para avanzar: normalmente 1 a 3 opciones relevantes, o una cotización puntual, o una sola promoción aplicable.
- Si la clienta pregunta por un servicio específico, responde primero sobre ese servicio y solo menciona extras estrictamente necesarios para cotizar bien.
- Si la clienta pide promociones, ofrece solo las promociones que sí apliquen a su intención actual; no mezcles paquetes de categorías no solicitadas.
- Evita saturar: descripciones cortas, sin repetir beneficios extensos ni incluir servicios de otras categorías salvo que la clienta los pida.
- Solo ofrece intervención humana si el cliente la solicita explícitamente, presenta una queja/frustración fuerte, o el caso no puede resolverse con la información documental. No uses intervención humana para dudas normales de servicios, precios, citas, capturas o agendamiento.

Base documental:
{docs_block}
""".strip()

    def _replace_placeholders(self, text: str, placeholders: dict[str, str]) -> str:
        result = text
        for placeholder, value in placeholders.items():
            result = result.replace(placeholder, value)
        return result


@lru_cache
def get_knowledge_engine() -> KnowledgeEngine:
    return KnowledgeEngine(get_settings().docs_path)
