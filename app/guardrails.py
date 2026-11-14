"""Controles de seguridad (alineados a OWASP LLM Top 10 a nivel básico)."""
import re

INJECTION_PATTERNS = [
    r"ignora (todas )?(las )?instrucciones", r"ignore (all |previous |the )*instructions",
    r"system prompt", r"prompt del sistema", r"a partir de ahora eres", r"you are now", r"jailbreak",
    r"revela (tu|el) (prompt|instrucciones)", r"developer mode",
]
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def detect_injection(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)


def ungrounded_numbers(answer: str, knowledge: str) -> list[str]:
    """Cifras en la respuesta que no aparecen en el CV: señal de posible alucinación."""
    known = set(NUM_RE.findall(knowledge))
    return sorted({n for n in NUM_RE.findall(answer) if n not in known and len(n) > 1})
