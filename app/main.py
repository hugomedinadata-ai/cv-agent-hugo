"""Servicio HTTP del agente de CV, compatible con Open Responses."""
import json
import logging
import time
from collections import OrderedDict

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from . import config
from .agent import CVAgent, INJECTION_REPLY
from .guardrails import ungrounded_numbers
from .openresponses import message_item, new_id, parse_input, response_obj, stream_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cv-agent")

app = FastAPI(title="Agente de CV de Hugo Medina", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
agent = CVAgent()
MODEL_NAME = "hugo-cv-agent"
# Memoria corta para previous_response_id (en memoria; se pierde si el servicio reinicia).
STORE: "OrderedDict[str, list]" = OrderedDict()
STORE_MAX = 500
# Límite de uso por IP (ventana de 60 s). En serverless es por instancia: protección básica.
RATE: dict = {}
RATE_LIMIT = int(__import__("os").getenv("RATE_LIMIT_PER_MIN", "30"))


def rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in RATE.get(ip, []) if now - t < 60]
    hits.append(now)
    RATE[ip] = hits
    return len(hits) > RATE_LIMIT


def error(status: int, etype: str, message: str, code: str | None = None, param: str | None = None):
    return JSONResponse(status_code=status, content={"error": {"type": etype, "code": code, "param": param, "message": message}})


def remember(resp_id: str, history: list, answer: str):
    STORE[resp_id] = history + [{"role": "assistant", "content": answer}]
    while len(STORE) > STORE_MAX:
        STORE.popitem(last=False)


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok", "agent": MODEL_NAME, "chunks": len(agent.retriever.chunks)}


@app.post("/v1/responses")
@app.post("/responses")
async def create_response(request: Request, authorization: str | None = Header(default=None)):
    if config.AGENT_API_KEY and authorization != f"Bearer {config.AGENT_API_KEY}":
        return error(401, "invalid_request", "API key inválida o ausente.", "invalid_api_key")
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0]
    if rate_limited(ip):
        return error(429, "too_many_requests", "Demasiadas solicitudes. Intenta en un minuto.", "rate_limit_exceeded")
    try:
        body = await request.json()
    except Exception:
        return error(400, "invalid_request", "El cuerpo debe ser JSON válido.")
    if "input" not in body:
        return error(400, "invalid_request", "Falta el campo 'input'.", "missing_required_parameter", "input")

    prev = body.get("previous_response_id")
    history = []
    if prev:
        if prev not in STORE:
            return error(404, "not_found", f"Previous response with id '{prev}' not found.",
                         "previous_response_not_found", "previous_response_id")
        history = list(STORE[prev])
    history += parse_input(body["input"])
    if not history or history[-1]["role"] != "user":
        return error(400, "invalid_request", "No hay un mensaje de usuario que responder.", param="input")

    instructions = body.get("instructions")
    model = body.get("model") or MODEL_NAME
    resp_id = new_id("resp")
    t0 = time.time()

    if body.get("stream"):
        msgs, meta = agent.prepare(history, instructions)
        chunks = iter([INJECTION_REPLY]) if msgs is None else agent.llm.stream(msgs)

        def finalize(text):
            meta["ungrounded_numbers"] = ungrounded_numbers(text, agent.retriever.full_text)
            meta["latency_ms"] = int((time.time() - t0) * 1000)
            remember(resp_id, history, text)
            log.info(json.dumps({"event": "answer", "stream": True, "id": resp_id, **meta}, ensure_ascii=False))
            return {"sources": ", ".join(meta.get("sources", []))[:500],
                    "ungrounded_numbers": ",".join(meta["ungrounded_numbers"]),
                    "latency_ms": str(meta["latency_ms"])}

        return StreamingResponse(stream_events(resp_id, model, prev, chunks, finalize),
                                 media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    try:
        text, usage, meta = agent.answer(history, instructions)
    except Exception as e:
        log.exception("model_error")
        return error(500, "model_error", "El servicio de IA no pudo generar una respuesta. Intenta nuevamente.", "model_error")
    remember(resp_id, history, text)
    out = response_obj(resp_id, model, int(t0), "completed", [message_item(text, new_id("msg"))],
                       usage=usage, prev=prev,
                       metadata={"sources": ", ".join(meta.get("sources", []))[:500],
                                 "ungrounded_numbers": ",".join(meta.get("ungrounded_numbers", [])),
                                 "latency_ms": str(meta.get("latency_ms", ""))})
    out["output_text"] = text  # atajo útil para clientes; no rompe la especificación
    return out
