"""Pruebas de resiliencia contra un servidor falso compatible con OpenAI (sin red ni llave).

Simula lo que se vio en Vercel: 503 del proveedor, lentitud (timeouts), modelo inexistente (404),
respuesta vacía y recuperación con modelo de respaldo. Verifica que nunca se exceda el presupuesto.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app import config
from app.llm import LLM, LLMError

CALLS: list[str] = []
MODE = {"by_model": {}}


def ok_body(model, text="Respuesta real simulada"):
    return {"id": "x", "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        model = body["model"]
        CALLS.append(model)
        behavior = MODE["by_model"].get(model, "ok")
        if behavior == "slow":
            time.sleep(3)
        if behavior in ("503", "404"):
            code = int(behavior)
            payload = {"error": {"code": code, "message": "upstream", "status": "UNAVAILABLE"}}
        elif behavior == "503_then_ok" and CALLS.count(model) == 1:
            code, payload = 503, {"error": {"code": 503, "message": "overloaded"}}
        elif behavior == "empty":
            code, payload = 200, ok_body(model, "")
        else:
            code, payload = 200, ok_body(model)
        data = json.dumps(payload).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1/"
    srv.shutdown()


@pytest.fixture
def llm(server, monkeypatch):
    CALLS.clear()
    MODE["by_model"] = {}
    for k, v in {"LLM_PROVIDER": "openai_compatible", "LLM_BASE_URL": server, "LLM_API_KEY": "test",
                 "LLM_MODEL": "main", "LLM_FALLBACK_MODEL": "", "LLM_ATTEMPT_TIMEOUT_S": 1.0,
                 "LLM_TOTAL_BUDGET_S": 8.0, "LLM_MAX_ATTEMPTS": 3, "LLM_RETRY_BASE_DELAY_S": 0.05}.items():
        monkeypatch.setattr(config, k, v)
    monkeypatch.setattr("app.llm.MIN_ATTEMPT_SECONDS", 0.5)
    return LLM


MSG = [{"role": "user", "content": "hola"}]


def test_ok(llm):
    text, usage = llm().complete(MSG)
    assert text and usage["attempts"] == 1 and CALLS == ["main"]


def test_503_luego_ok_se_recupera(llm):
    MODE["by_model"] = {"main": "503_then_ok"}
    text, usage = llm().complete(MSG)
    assert text and usage["attempts"] == 2


def test_503_persistente_da_error_tipado(llm):
    MODE["by_model"] = {"main": "503"}
    with pytest.raises(LLMError) as e:
        llm().complete(MSG)
    assert e.value.code == "model_unavailable" and e.value.http_status == 503
    assert e.value.upstream_status == 503 and len(CALLS) == 3


def test_respaldo_rescata(llm, monkeypatch):
    monkeypatch.setattr(config, "LLM_FALLBACK_MODEL", "lite")
    MODE["by_model"] = {"main": "503", "lite": "ok"}
    text, usage = llm().complete(MSG)
    assert usage["model"] == "lite" and CALLS == ["main", "main", "lite"]


def test_404_no_reintenta(llm):
    MODE["by_model"] = {"main": "404"}
    with pytest.raises(LLMError) as e:
        llm().complete(MSG)
    assert e.value.code == "model_not_found" and CALLS == ["main"]


def test_lento_respeta_presupuesto(llm, monkeypatch):
    monkeypatch.setattr(config, "LLM_TOTAL_BUDGET_S", 2.5)
    MODE["by_model"] = {"main": "slow"}
    t0 = time.monotonic()
    with pytest.raises(LLMError) as e:
        llm().complete(MSG)
    assert e.value.code == "model_timeout"
    assert time.monotonic() - t0 < 2.5 + 0.5  # nunca se pasa del presupuesto


def test_respuesta_vacia(llm):
    MODE["by_model"] = {"main": "empty"}
    with pytest.raises(LLMError) as e:
        llm().complete(MSG)
    assert e.value.code == "model_empty_response"


def test_endpoint_devuelve_503_tipado(llm, monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as m
    monkeypatch.setattr(m.agent, "llm", llm())
    monkeypatch.setattr(config, "AGENT_API_KEY", "")
    m.RATE.clear()
    MODE["by_model"] = {"main": "503"}
    r = TestClient(m.app).post("/v1/responses", json={"input": "¿Qué logró Hugo?"})
    assert r.status_code == 503 and r.headers.get("retry-after") == "5"
    assert r.json()["error"]["code"] == "model_unavailable"
    assert "test" not in r.text  # la llave nunca aparece


def test_plan_incluye_respaldo_por_defecto(llm, monkeypatch):
    monkeypatch.setattr(config, "LLM_FALLBACK_MODEL", "lite")
    instance = llm()
    assert instance._plan() == ["main", "main", "lite"]
