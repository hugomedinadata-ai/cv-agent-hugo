"""Servicio HTTP del agente de CV, compatible con Open Responses."""
import hmac
import json
import logging
import time
from collections import OrderedDict

from redis.asyncio import Redis

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from . import config
from .agent import CVAgent, INJECTION_REPLY
from .guardrails import ungrounded_numbers
from .llm import LLMError
from .openresponses import message_item, new_id, parse_input, response_obj, stream_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cv-agent")

app = FastAPI(title="Agente de CV de Hugo Medina", version="1.0.0")
allowed_origins = [origin.strip() for origin in __import__("os").getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
agent = CVAgent()
MODEL_NAME = "hugo-cv-agent"
STORE: "OrderedDict[str, list]" = OrderedDict()
STORE_MAX = 500
RATE: dict = {}
RATE_LIMIT = int(__import__("os").getenv("RATE_LIMIT_PER_MIN", "30"))
redis_client = Redis.from_url(config.REDIS_URL, decode_responses=True) if config.REDIS_URL else None


class RateLimitStoreUnavailable(Exception):
    """Raised when the configured shared rate-limit store cannot be reached."""




def authorized(authorization: str | None) -> bool:
    """Fail closed: no se permite tráfico si el secreto no está configurado."""
    expected = config.AGENT_API_KEY
    if not expected or not authorization:
        return False
    return hmac.compare_digest(authorization, f"Bearer {expected}")


async def rate_limited(ip: str) -> bool:
    if redis_client is not None:
        # Atomic fixed-window counter shared across all application instances.
        key = f"cv-agent:rate:{ip}"
        script = """
        local count = redis.call('INCR', KEYS[1])
        if count == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return count
        """
        try:
            count = await redis_client.eval(script, 1, key, config.RATE_WINDOW_SECONDS)
        except Exception as exc:
            log.exception("rate_limit_store_unavailable")
            raise RateLimitStoreUnavailable from exc
        return int(count) > RATE_LIMIT

    # Local fallback for development and single-instance deployments only.
    now = time.time()
    hits = [t for t in RATE.get(ip, []) if now - t < config.RATE_WINDOW_SECONDS]
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


@app.get("/health/llm")
def health_llm(authorization: str | None = Header(default=None)):
    """Diagnóstico real del modelo (consume cuota); requiere API key."""
    if not authorized(authorization):
        return error(401, "invalid_request", "API key inválida o ausente.", "invalid_api_key")
    result = agent.llm.ping()
    return JSONResponse(status_code=200 if result.get("ok") else 503, content=result)


@app.post("/v1/responses")
@app.post("/responses")
async def create_response(request: Request, authorization: str | None = Header(default=None)):
    if not authorized(authorization):
        return error(401, "invalid_request", "API key inválida o ausente.", "invalid_api_key")

    # No confiar en X-Forwarded-For enviado por el cliente: puede falsificarse.
    ip = request.client.host if request.client else "unknown"
    try:
        limited = await rate_limited(ip)
    except RateLimitStoreUnavailable:
        response = error(503, "server_error", "El control de tráfico no está disponible.", "rate_limit_store_unavailable")
        response.headers["Retry-After"] = "5"
        return response
    if limited:
        return error(429, "too_many_requests", "Demasiadas solicitudes. Intenta en un minuto.", "rate_limit_exceeded")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > config.MAX_REQUEST_BYTES:
                return error(413, "invalid_request", "El cuerpo de la solicitud excede el tamaño permitido.", "request_too_large")
        except ValueError:
            return error(400, "invalid_request", "Content-Length inválido.")

    # Leer en streaming y detenerse al superar el límite; evita acumular cuerpos
    # arbitrariamente grandes cuando Content-Length no está presente o es falso.
    raw_body = bytearray()
    async for chunk in request.stream():
        if len(raw_body) + len(chunk) > config.MAX_REQUEST_BYTES:
            return error(413, "invalid_request", "El cuerpo de la solicitud excede el tamaño permitido.", "request_too_large")
        raw_body.extend(chunk)
    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error(400, "invalid_request", "El cuerpo debe ser JSON válido.")
    if not isinstance(body, dict):
        return error(400, "invalid_request", "El cuerpo debe ser un objeto JSON.")
    if "input" not in body:
        return error(400, "invalid_request", "Falta el campo 'input'.", "missing_required_parameter", "input")

    prev = body.get("previous_response_id")
    history = []
    if prev:
        if not isinstance(prev, str) or prev not in STORE:
            return error(404, "not_found", "Previous response not found.",
                         "previous_response_not_found", "previous_response_id")
        history = list(STORE[prev])
    history += parse_input(body["input"])
    if not history or history[-1]["role"] != "user":
        return error(400, "invalid_request", "No hay un mensaje de usuario que responder.", param="input")

    model = body.get("model") or MODEL_NAME
    resp_id = new_id("resp")
    t0 = time.time()

    if body.get("stream"):
        # Las instrucciones del cliente no se elevan al prompt del sistema.
        msgs, meta = agent.prepare(history)
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
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    try:
        text, usage, meta = agent.answer(history)
    except LLMError as e:
        log.error(json.dumps({"event": "llm_error", "id": resp_id, **e.diagnostics()}))
        resp = error(e.http_status, "server_error", e.message, e.code)
        if e.http_status == 503:
            resp.headers["Retry-After"] = "5"
        return resp
    except Exception:
        log.exception("unexpected_error")
        return error(500, "server_error", "Error interno del agente.", "internal_error")
    remember(resp_id, history, text)
    out = response_obj(resp_id, model, int(t0), "completed", [message_item(text, new_id("msg"))],
                       usage=usage, prev=prev,
                       metadata={"sources": ", ".join(meta.get("sources", []))[:500],
                                 "ungrounded_numbers": ",".join(meta.get("ungrounded_numbers", [])),
                                 "latency_ms": str(meta.get("latency_ms", "")),
                                 "llm_model": str(meta.get("llm_model") or ""),
                                 "llm_attempts": str(meta.get("llm_attempts") or "")})
    out["output_text"] = text
    return out
