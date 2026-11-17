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
    """Valida y convierte input en mensajes user/assistant; nunca degrada roles desconocidos a user."""
    if isinstance(raw, str):
        if not raw.strip():
            raise ValueError("input text must not be empty")
        return [{"role": "user", "content": raw}]
    if not isinstance(raw, list) or not raw:
        raise ValueError("input must be non-empty text or a message array")
    history = []
    for item in raw:
        if not isinstance(item, dict) or item.get("type", "message") != "message":
            raise ValueError("each input item must be a message")
        role = item.get("role")
        if role not in ("user", "assistant"):
            raise ValueError("only user and assistant roles are accepted")
        text = _text_of(item.get("content"))
        if not text.strip():
            raise ValueError("message content must not be empty")
        history.append({"role": role, "content": text})
    return history


def _valid_alternation(history: list[dict]) -> bool:
    if not isinstance(history, list) or not history or not isinstance(history[0], dict):
        return False
    if history[0].get("role") != "user":
        return False
    return all(isinstance(message, dict)
               and message.get("role") == ("user" if index % 2 == 0 else "assistant")
               and isinstance(message.get("content"), str)
               and bool(message["content"].strip())
               for index, message in enumerate(history))


def validate_history(history: list[dict]) -> bool:
    """Enforce a user-started, alternating conversation ending in a user turn."""
    return bool(_valid_alternation(history) and history[-1]["role"] == "user")


def validate_stored_history(history: list[dict]) -> bool:
    """Validate a persisted conversation ending in the assistant response."""
    return bool(_valid_alternation(history) and history[-1]["role"] == "assistant")


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


async def stream_events(resp_id, model, prev, chunks, finalize):
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
    except Exception:  # no exponer mensajes crudos del proveedor ni credenciales
        failed = response_obj(resp_id, model, created, "failed", [], prev=prev)
        failed["error"] = {"type": "server_error", "code": "stream_failed",
                           "message": "The response stream could not be completed."}
        yield ev(type="error", error=failed["error"])
        yield ev(type="response.failed", response=failed)
        return
    part = {"type": "output_text", "text": text, "annotations": []}
    yield ev(type="response.output_text.done", item_id=item_id, output_index=0, content_index=0, text=text, logprobs=[])
    yield ev(type="response.content_part.done", item_id=item_id, output_index=0, content_index=0, part=part)
    item = message_item(text, item_id)
    yield ev(type="response.output_item.done", output_index=0, item=item)
    try:
        metadata = await finalize(text)
    except Exception:
        failed = response_obj(resp_id, model, created, "failed", [], prev=prev)
        failed["error"] = {"type": "server_error", "code": "session_store_unavailable",
                           "message": "The conversation could not be saved."}
        yield ev(type="error", error=failed["error"])
        yield ev(type="response.failed", response=failed)
        return
    final = response_obj(resp_id, model, created, "completed", [item], prev=prev, metadata=metadata)
    yield ev(type="response.completed", response=final)
