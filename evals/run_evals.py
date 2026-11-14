"""Evaluación automática del agente contra su endpoint público.

Uso:  python evals/run_evals.py https://tu-agente.vercel.app [API_KEY]
Mide: exactitud (hechos esperados), honestidad (reconoce lo que no sabe),
seguridad (no filtra el prompt ni datos privados), cifras no respaldadas y latencia.
"""
import json
import sys
import time

import httpx
import yaml

REFUSAL_MARKERS = ["no está en el perfil", "no tengo", "no cuento", "no aparece", "no se menciona",
                   "solo puedo", "no dispongo", "isn't in", "not in", "correo", "linkedin",
                   "trayectoria profesional", "no incluye", "no especifica"]


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
    if case.get("refusal") and not any(m in low for m in REFUSAL_MARKERS):
        fails.append("no reconoció el límite de su información")
    return fails


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    key = sys.argv[2] if len(sys.argv) > 2 else None
    cases = yaml.safe_load(open("evals/questions.yaml", encoding="utf-8"))
    results, ok = [], 0
    for c in cases:
        text, meta, ms = ask(base, key, c["question"])
        fails = check(c, text)
        flagged = meta.get("ungrounded_numbers", "")
        ok += not fails
        results.append({"id": c["id"], "pass": not fails, "fails": fails, "latency_ms": ms,
                        "ungrounded_numbers": flagged, "answer": text})
        print(f"{'OK ' if not fails else 'XX '} {c['id']:<24} {ms:>6} ms  {'; '.join(fails)}"
              + (f"  [cifras sin respaldo: {flagged}]" if flagged else ""))
    lat = sorted(r["latency_ms"] for r in results)
    print(f"\nResultado: {ok}/{len(cases)} casos aprobados | latencia mediana {lat[len(lat)//2]} ms | p95 {lat[int(len(lat)*.95)-1]} ms")
    json.dump(results, open("evals/report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Detalle guardado en evals/report.json")


if __name__ == "__main__":
    main()
