HUMAN_HANDOVER_MARKERS = (
    "humano",
    "persona",
    "asesora",
    "asesor",
    "gerente",
    "queja",
    "molesta",
    "molesto",
    "enojada",
    "enojado",
    "pésimo",
    "pesimo",
    "mal servicio",
)


def needs_human_handover(message: str) -> bool:
    normalized = message.casefold()
    return any(marker in normalized for marker in HUMAN_HANDOVER_MARKERS)


def human_handover_reply() -> str:
    return (
        "Con gusto. Soy Sofía de Vanity Nail Salon; voy a pausar el flujo automático "
        "para que una persona del equipo tome tu conversación en breve."
    )
