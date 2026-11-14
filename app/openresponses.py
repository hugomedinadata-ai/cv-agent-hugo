"""Traducción entre la especificación Open Responses (POST /v1/responses) y el agente."""
import json
import time
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content
                         if isinstance(p, dict) and p.get("type") in ("input_text", "output_text", "text"))
    return ""


def parse_input(raw) -> list[dict]:
    """Convierte `input` (texto o lista de items) en historial [{role, content}]."""
    if isinstance(raw, str):
        return [{"role": "user", "content": raw}]
    history = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        if item.get("type", "message") != "message":
            continue  # function_call, reasoning, etc.: este agente no usa herramientas externas
        role = item.get("role", "user")
        if role in ("system", "developer"):
            continue  # el rol de sistema lo define el servidor (defensa contra inyección)
        text = _text_of(item.get("content"))
        if text:
            history.append({"role": "assistant" if role == "assistant" else "user", "content": text})
    return history


def message_item(text: str, item_id: str, status: str = "completed") -> dict:
    content = [{"type": "output_text", "text": text, "annotations": []}] if status == "completed" else []
    return {"id": item_id, "type": "message", "status": status, "role": "assistant", "content": content}


def response_obj(resp_id, model, created, status, output, usage=None, prev=None, metadata=None) -> dict:
    return {
        "id": resp_id, "object": "response", "created_at": created, "status": status,
        "model": model, "output": output, "previous_response_id": prev,
        "usage": usage or None, "error": None, "incomplete_details": None,
        "metadata": metadata or {},
    }


def sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def stream_events(resp_id, model, prev, chunks, finalize):
    """Genera la secuencia de eventos semánticos de la especificación."""
    created = int(time.time())
    item_id = new_id("msg")
    seq = 0

    def ev(**kw):
        nonlocal seq
        kw["sequence_number"] = seq
        seq += 1
        return sse(kw)

    base = response_obj(resp_id, model, created, "in_progress", [], prev=prev)
    yield ev(type="response.created", response=base)
    yield ev(type="response.in_progress", response=base)
    yield ev(type="response.output_item.added", output_index=0, item=message_item("", item_id, "in_progress"))
    yield ev(type="response.content_part.added", item_id=item_id, output_index=0, content_index=0,
             part={"type": "output_text", "text": "", "annotations": []})
    text = ""
    try:
        for delta in chunks:
            text += delta
            yield ev(type="response.output_text.delta", item_id=item_id, output_index=0,
                     content_index=0, delta=delta, logprobs=[])
    except Exception as e:  # el modelo falló a mitad del stream
        failed = response_obj(resp_id, model, created, "failed", [], prev=prev)
        failed["error"] = {"type": "model_error", "code": "model_error", "message": str(e)[:200]}
        yield ev(type="error", error=failed["error"])
        yield ev(type="response.failed", response=failed)
        return
    part = {"type": "output_text", "text": text, "annotations": []}
    yield ev(type="response.output_text.done", item_id=item_id, output_index=0, content_index=0, text=text, logprobs=[])
    yield ev(type="response.content_part.done", item_id=item_id, output_index=0, content_index=0, part=part)
    item = message_item(text, item_id)
    yield ev(type="response.output_item.done", output_index=0, item=item)
    final = response_obj(resp_id, model, created, "completed", [item], prev=prev, metadata=finalize(text))
    yield ev(type="response.completed", response=final)
