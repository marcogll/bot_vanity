from datetime import datetime
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


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
            raise FileNotFoundError(f"Missing knowledge documents: {', '.join(missing)}")

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
        docs_block = "\n\n".join(
            f"--- {filename} ---\n{content}" for filename, content in self._documents.items()
        )
        memory = memory_context or "Sin contexto previo disponible."

        return f"""
Fecha y hora actual del sistema: {current_datetime.isoformat()}
Liga oficial de agendamiento Fresh: {get_settings().booking_url}

Contexto previo del cliente:
{memory}

Reglas operativas obligatorias:
- No proporciones la liga de agendamiento hasta haber preguntado por Retiro y Nail Art cuando el servicio sea de uñas.
- Si el cliente busca pestañas, pregunta por Retiro de Pestañas antes de cotizar o cerrar.
- Usa solo precios, duraciones y promociones presentes en los documentos.
- Valida promociones temporales contra la fecha actual antes de ofrecerlas.
- Si falta información para cotizar, pregunta una cosa concreta antes de avanzar.
- Si detectas frustración o solicitud humana, indica que una persona del equipo tomará la conversación.

Base documental:
{docs_block}
""".strip()


@lru_cache
def get_knowledge_engine() -> KnowledgeEngine:
    return KnowledgeEngine(get_settings().docs_path)
