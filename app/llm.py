"""Cliente de modelo. Decisión: interfaz compatible con OpenAI para poder cambiar de
proveedor (Gemini, Groq, OpenRouter, Azure OpenAI) solo con variables de entorno."""
from typing import Iterator
from . import config


class LLM:
    def __init__(self):
        self.mock = config.LLM_PROVIDER == "mock"
        if not self.mock:
            from openai import OpenAI
            self.client = OpenAI(
    base_url=config.LLM_BASE_URL,
    api_key=config.LLM_API_KEY,
    timeout=50,
    max_retries=0,
)

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        if self.mock:
            ctx = messages[0]["content"].split("CONTEXTO:")[-1].strip().splitlines()
            return "Respuesta de prueba basada en el CV: " + (ctx[1] if len(ctx) > 1 else ""), {}
        r = self.client.chat.completions.create(model=config.LLM_MODEL, messages=messages,
                                                temperature=config.TEMPERATURE,
                                                max_tokens=config.MAX_OUTPUT_TOKENS)
        u = r.usage
        usage = {"input_tokens": u.prompt_tokens, "output_tokens": u.completion_tokens,
                 "total_tokens": u.total_tokens} if u else {}
        return r.choices[0].message.content or "", usage

    def stream(self, messages: list[dict]) -> Iterator[str]:
        if self.mock:
            text, _ = self.complete(messages)
            for w in text.split(" "):
                yield w + " "
            return
        r = self.client.chat.completions.create(model=config.LLM_MODEL, messages=messages,
                                                temperature=config.TEMPERATURE,
                                                max_tokens=config.MAX_OUTPUT_TOKENS, stream=True)
        for ch in r:
            if ch.choices and ch.choices[0].delta and ch.choices[0].delta.content:
                yield ch.choices[0].delta.content
