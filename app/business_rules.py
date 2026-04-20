HUMAN_HANDOVER_REQUEST_MARKERS = (
    "hablar con un humano",
    "hablar con una persona",
    "hablar con alguien",
    "quiero un humano",
    "quiero una persona",
    "quiero hablar con asesora",
    "quiero hablar con asesor",
    "pásame con asesora",
    "pasame con asesora",
    "pásame con asesor",
    "pasame con asesor",
    "pásame con alguien",
    "pasame con alguien",
    "gerente",
)

HUMAN_HANDOVER_ESCALATION_MARKERS = (
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
    return any(marker in normalized for marker in HUMAN_HANDOVER_REQUEST_MARKERS) or any(
        marker in normalized for marker in HUMAN_HANDOVER_ESCALATION_MARKERS
    )


def human_handover_reply() -> str:
    return (
        "Con gusto. Soy Sofía de Vanity Nail Salon; voy a pausar el flujo automático "
        "para que una persona del equipo tome tu conversación en breve."
    )
