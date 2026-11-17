"""Evaluación automática del agente contra su endpoint.

Uso: python evals/run_evals.py https://tu-agente.vercel.app [API_KEY]
Los marcadores de rechazo deben expresar falta de información o un límite explícito;
mencionar datos de contacto o la trayectoria no cuenta como rechazo.
"""
import json
import sys
import time

import httpx
import yaml

REFUSAL_MARKERS = [
    "no está documentado", "no se encuentra documentado", "no está en la información",
    "no aparece en la información", "no se menciona en el perfil",
    "no tengo información", "no cuento con información", "no dispongo de información",
    "no puedo confirmar", "no se especifica", "no está especificado",
    "isn't documented", "not documented", "i don't have information",
    "i cannot confirm", "not specified",
]
SCOPE_MARKERS = [
    "solo puedo conversar sobre la trayectoria profesional",
    "puedo ayudar con información profesional", "fuera del alcance",
    "no está relacionado con la trayectoria profesional",
]


def ask(base, key, q):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    t0 = time.time()
    r = httpx.post(f"{base.rstrip('/')}/v1/responses", json={"model": "hugo-cv-agent", "input": q},
                   headers=headers, timeout=60)
    r.raise_for_status()
    body = r.json()
    text = body["output"][0]["content"][0]["text"]
    return text, body.get("metadata", {}), int((time.time() - t0) * 1000)


def check(case, text):
    low = text.lower()
    fails = []
    for group in case.get("must_include", []):
        if not any(opt.lower() in low for opt in group):
            fails.append(f"falta uno de {group}")
    for bad in case.get("must_not_include", []):
        if bad.lower() in low:
            fails.append(f"no debía decir '{bad}'")
    if case.get("refusal"):
        markers = REFUSAL_MARKERS + (SCOPE_MARKERS if case.get("scope_refusal") else [])
        if not any(m in low for m in markers):
            fails.append("no reconoció explícitamente la falta de información o el límite de alcance")
    return fails


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    key = sys.argv[2] if len(sys.argv) > 2 else None
    with open("evals/questions.yaml", encoding="utf-8") as f:
        cases = yaml.safe_load(f)
    results, ok = [], 0
    for c in cases:
        text, meta, ms = ask(base, key, c["question"])
        fails = check(c, text)
        flagged = meta.get("ungrounded_numbers", "")
        ok += not fails
        results.append({"id": c["id"], "pass": not fails, "fails": fails, "latency_ms": ms,
                        "ungrounded_numbers": flagged, "answer": text})
        print(f"{'OK ' if not fails else 'XX '} {c['id']:<32} {ms:>6} ms  {'; '.join(fails)}"
              + (f"  [revisar cifras: {flagged}]" if flagged else ""))
    lat = sorted(r["latency_ms"] for r in results)
    if lat:
        p95_index = min(len(lat) - 1, int(len(lat) * .95))
        print(f"\nResultado: {ok}/{len(cases)} casos aprobados | latencia mediana {lat[len(lat)//2]} ms | p95 {lat[p95_index]} ms")
    json.dump(results, open("evals/report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Detalle guardado en evals/report.json")


if __name__ == "__main__":
    main()
