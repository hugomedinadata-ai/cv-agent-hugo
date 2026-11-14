"""Recuperación de contexto sobre el CV.

Decisión: BM25 léxico sobre secciones del CV en Markdown.
- El corpus es pequeño (unas 15 secciones), así que no se justifica una base vectorial.
- BM25 es determinista, explicable y no cuesta llamadas a un modelo de embeddings.
- Siempre se incluye el resumen profesional para dar contexto general.
Si el corpus creciera (proyectos, publicaciones), el siguiente paso sería búsqueda
híbrida (BM25 + embeddings) con reranking.
"""
import glob
import math
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

STOPWORDS = set("""a al algo como con cual cuales de del el ella en es esa ese esta este fue ha
hay la las le lo los mas me mi muy no o para pero por que se sin sobre su sus te tu un una
uno y ya the of and to in is what who how his he does did tiene tuvo hizo hace cual cuál
qué que quien quién cómo como donde dónde cuando cuándo hugo""".split())

SYNONYMS = {
    "logro": ["redujo", "reduccion", "resultado"], "logros": ["redujo", "reduccion", "resultado"],
    "estudios": ["educacion", "maestria", "ingenieria"], "estudio": ["educacion", "maestria"],
    "ingles": ["ingles", "b2"], "english": ["ingles", "b2"], "contacto": ["correo", "linkedin"],
    "contactar": ["correo", "linkedin"], "ia": ["inteligencia", "artificial", "copilot", "agente"],
    "equipo": ["equipo", "lideraba", "personas"], "nube": ["aws", "cloud"], "cloud": ["aws"],
    "gobierno": ["gobierno", "linaje", "metadata", "calidad"], "herramientas": ["habilidades", "tecnicas"],
}


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


@dataclass
class Chunk:
    source: str
    title: str
    text: str
    tokens: list


class Retriever:
    def __init__(self, knowledge_dir: str, k1: float = 1.5, b: float = 0.75):
        self.chunks: list[Chunk] = []
        for path in sorted(glob.glob(os.path.join(knowledge_dir, "*.md"))):
            with open(path, encoding="utf-8") as f:
                content = f.read()
            for block in re.split(r"^## ", content, flags=re.M):
                block = block.strip()
                if not block:
                    continue
                title, _, body = block.partition("\n")
                self.chunks.append(Chunk(os.path.basename(path), title.strip(), body.strip(),
                                         normalize(title + " " + body)))
        self.k1, self.b = k1, b
        self.avgdl = sum(len(c.tokens) for c in self.chunks) / max(len(self.chunks), 1)
        df = Counter(t for c in self.chunks for t in set(c.tokens))
        n = len(self.chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _score(self, q: list[str], c: Chunk) -> float:
        tf = Counter(c.tokens)
        s = 0.0
        for t in q:
            if t not in tf:
                continue
            f = tf[t]
            s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(c.tokens) / self.avgdl))
        return s

    def search(self, query: str, top_k: int = 4) -> list[Chunk]:
        q = normalize(query)
        q += [s for t in q for s in SYNONYMS.get(t, [])]
        ranked = sorted(self.chunks, key=lambda c: self._score(q, c), reverse=True)
        hits = [c for c in ranked[:top_k] if self._score(q, c) > 0]
        if not hits:  # pregunta general ("cuéntame de Hugo"): panorama de su trayectoria
            overview = ("Citibanamex: rol", "Citibanamex: logro", "Grupo Salinas", "BBVA", "Habilidades")
            hits = [c for c in self.chunks if c.title.startswith(overview)]
        summary = next((c for c in self.chunks if c.title.startswith("Resumen")), None)
        if summary and summary not in hits:
            hits.insert(0, summary)
        return hits

    @property
    def full_text(self) -> str:
        return "\n".join(c.text for c in self.chunks)
