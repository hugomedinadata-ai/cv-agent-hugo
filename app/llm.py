"""Cliente de modelo con presupuesto de tiempo total y reintentos acotados.

Principios:
1. Presupuesto total (LLM_TOTAL_BUDGET_S) para TODOS los intentos, por debajo del límite
   de la función de Vercel (60 s). Ningún reintento puede empujar la ejecución al timeout.
2. Cada intento usa como timeout el menor entre LLM_ATTEMPT_TIMEOUT_S y el tiempo que resta.
3. Solo se reintenta lo transitorio (timeout, conexión, 429/500/502/503/504).
4. Si el modelo principal está saturado, el último intento puede ir a LLM_FALLBACK_MODEL.
5. `reasoning_effort` controla el "pensamiento" de Gemini: menos pensamiento = menos latencia.
6. Los errores salen como LLMError con un código seguro (sin llaves ni texto crudo del proveedor).
"""
import logging
import random
import time
from typing import Iterator

from . import config

log = logging.getLogger("cv-agent.llm")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MIN_ATTEMPT_SECONDS = 5.0  # si queda menos tiempo, no vale la pena otro intento


class LLMError(Exception):
    """Error del proveedor del modelo, ya clasificado para responder al cliente."""

    def __init__(self, code: str, http_status: int, message: str, upstream_status: int | None = None,
                 attempts: int = 0, elapsed_ms: int = 0, model: str = ""):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.upstream_status = upstream_status
        self.attempts = attempts
        self.elapsed_ms = elapsed_ms
        self.model = model

    def diagnostics(self) -> dict:
        return {"code": self.code, "upstream_status": self.upstream_status, "attempts": self.attempts,
                "elapsed_ms": self.elapsed_ms, "model": self.model}


def classify(exc: Exception, model: str) -> LLMError:
    """Traduce una excepción del SDK a un LLMError seguro."""
    from openai import APIConnectionError, APIStatusError, APITimeoutError

    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, APITimeoutError):  # va antes: es subclase de APIConnectionError
        return LLMError("model_timeout", 504, "El modelo tardó demasiado en responder.", model=model)
    if isinstance(exc, APIConnectionError):
        return LLMError("model_unreachable", 502, "No se pudo conectar con el proveedor del modelo.", model=model)
    if isinstance(exc, APIStatusError):
        s = exc.status_code
        if s in (401, 403):
            return LLMError("model_auth_error", 502, "El proveedor rechazó la credencial del modelo (revisar LLM_API_KEY).", s, model=model)
        if s == 404:
            return LLMError("model_not_found", 502, f"El modelo '{model}' no existe o no está disponible para esta llave.", s, model=model)
        if s == 400:
            return LLMError("model_bad_request", 502, "El proveedor rechazó los parámetros de la solicitud.", s, model=model)
        if s == 429:
            return LLMError("model_rate_limited", 503, "Se alcanzó la cuota del proveedor del modelo.", s, model=model)
        if s in RETRYABLE_STATUS_CODES:
            return LLMError("model_unavailable", 503, "El proveedor del modelo está saturado o no disponible.", s, model=model)
        return LLMError("model_error", 502, "El proveedor del modelo devolvió un error.", s, model=model)
    return LLMError("model_error", 500, "Error inesperado al llamar al modelo.", model=model)


def is_retryable(err: LLMError) -> bool:
    return err.code in ("model_timeout", "model_unreachable", "model_unavailable", "model_rate_limited")


class LLM:
    def __init__(self):
        self.mock = config.LLM_PROVIDER == "mock"
        if not self.mock:
            from openai import OpenAI
            # max_retries=0: los reintentos los controla este módulo, con presupuesto de tiempo.
            self.client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY,
                                 timeout=config.LLM_ATTEMPT_TIMEOUT_S, max_retries=0)

    def _plan(self) -> list[str]:
        plan = [config.LLM_MODEL] * max(1, config.LLM_MAX_ATTEMPTS)
        fb = config.LLM_FALLBACK_MODEL
        if fb and fb != config.LLM_MODEL and len(plan) > 1:
            plan[-1] = fb  # el último intento va al modelo de respaldo
        return plan

    def _params(self, model: str, messages: list[dict], timeout: float, stream: bool) -> dict:
        p = {"model": model, "messages": messages, "temperature": config.TEMPERATURE,
             "max_tokens": config.MAX_OUTPUT_TOKENS, "timeout": timeout}
        if config.LLM_REASONING_EFFORT:
            p["reasoning_effort"] = config.LLM_REASONING_EFFORT
        if stream:
            p["stream"] = True
        return p

    def _call_with_budget(self, messages: list[dict], stream: bool = False):
        """Intenta el plan de modelos sin exceder el presupuesto total de tiempo."""
        t0 = time.monotonic()
        deadline = t0 + config.LLM_TOTAL_BUDGET_S
        last: LLMError | None = None
        for i, model in enumerate(self._plan(), start=1):
            remaining = deadline - time.monotonic()
            if remaining < MIN_ATTEMPT_SECONDS:
                break
            timeout = min(config.LLM_ATTEMPT_TIMEOUT_S, remaining)
            try:
                result = self.client.chat.completions.create(**self._params(model, messages, timeout, stream))
                if i > 1:
                    log.info("llm_recovered attempt=%s model=%s", i, model)
                return result, model, i
            except Exception as exc:  # noqa: BLE001 — se clasifica abajo
                last = classify(exc, model)
                last.attempts = i
                last.elapsed_ms = int((time.monotonic() - t0) * 1000)
                log.warning("llm_attempt_failed attempt=%s model=%s code=%s upstream=%s elapsed_ms=%s",
                            i, model, last.code, last.upstream_status, last.elapsed_ms)
                if not is_retryable(last):
                    raise last
                delay = min(config.LLM_RETRY_BASE_DELAY_S * (2 ** (i - 1)), 4.0) + random.uniform(0, 0.3)
                if deadline - time.monotonic() - delay < MIN_ATTEMPT_SECONDS:
                    break
                time.sleep(delay)
        if last is None:
            last = LLMError("model_timeout", 504, "No hubo tiempo suficiente para consultar el modelo.")
        last.elapsed_ms = int((time.monotonic() - t0) * 1000)
        raise last

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        if self.mock:
            ctx = messages[0]["content"].split("CONTEXTO:")[-1].strip().splitlines()
            return "Respuesta de prueba basada en el CV: " + (ctx[1] if len(ctx) > 1 else ""), {}

        r, model, attempts = self._call_with_budget(messages)
        text = (r.choices[0].message.content or "") if r.choices else ""
        if not text.strip():
            # Pasa con modelos que "piensan": el límite de tokens se gasta antes de escribir.
            raise LLMError("model_empty_response", 502,
                           "El modelo no devolvió texto (revisar MAX_OUTPUT_TOKENS o LLM_REASONING_EFFORT).",
                           attempts=attempts, model=model)
        u = r.usage
        usage = {"input_tokens": u.prompt_tokens, "output_tokens": u.completion_tokens,
                 "total_tokens": u.total_tokens} if u else {}
        usage["model"] = model
        usage["attempts"] = attempts
        return text, usage

    def stream(self, messages: list[dict]) -> Iterator[str]:
        """Los reintentos aplican antes del primer token; un corte a mitad se reporta como fallo."""
        if self.mock:
            text, _ = self.complete(messages)
            for w in text.split(" "):
                yield w + " "
            return
        r, model, _ = self._call_with_budget(messages, stream=True)
        try:
            for ch in r:
                if ch.choices and ch.choices[0].delta and ch.choices[0].delta.content:
                    yield ch.choices[0].delta.content
        except Exception as exc:  # noqa: BLE001
            raise classify(exc, model) from None

    def ping(self) -> dict:
        """Prueba mínima del modelo para diagnóstico (sin exponer secretos)."""
        if self.mock:
            return {"ok": True, "model": "mock"}
        t0 = time.monotonic()
        try:
            text, usage = self.complete([{"role": "user", "content": "Responde solo: OK"}])
            return {"ok": True, "model": usage.get("model"), "attempts": usage.get("attempts"),
                    "latency_ms": int((time.monotonic() - t0) * 1000), "sample": text[:40]}
        except LLMError as e:
            return {"ok": False, "message": e.message, **e.diagnostics()}
