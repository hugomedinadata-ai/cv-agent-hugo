
"""Cliente de modelo con reintentos acotados para errores transitorios."""
import logging
import random
import time
from typing import Iterator

from . import config

log = logging.getLogger("cv-agent.llm")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (1.0, 2.0)


class LLM:
    def __init__(self):
        self.mock = config.LLM_PROVIDER == "mock"
        if not self.mock:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=config.LLM_BASE_URL,
                api_key=config.LLM_API_KEY,
                timeout=15,
                max_retries=0,
            )

    def _create_with_retry(self, messages: list[dict]):
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        for attempt in range(MAX_ATTEMPTS):
            try:
                return self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    temperature=config.TEMPERATURE,
                    max_tokens=config.MAX_OUTPUT_TOKENS,
                )
            except (APITimeoutError, APIConnectionError):
                if attempt == MAX_ATTEMPTS - 1:
                    raise
                delay = RETRY_DELAYS_SECONDS[attempt] + random.uniform(0, 0.3)
                log.warning(
                    "Transient LLM connection/timeout error; retry %s/%s in %.1fs",
                    attempt + 1, MAX_ATTEMPTS - 1, delay,
                )
                time.sleep(delay)
            except APIStatusError as exc:
                if exc.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_ATTEMPTS - 1:
                    raise
                delay = RETRY_DELAYS_SECONDS[attempt] + random.uniform(0, 0.3)
                log.warning(
                    "LLM provider returned HTTP %s; retry %s/%s in %.1fs",
                    exc.status_code, attempt + 1, MAX_ATTEMPTS - 1, delay,
                )
                time.sleep(delay)

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        if self.mock:
            ctx = messages[0]["content"].split("CONTEXTO:")[-1].strip().splitlines()
            return "Respuesta de prueba basada en el CV: " + (ctx[1] if len(ctx) > 1 else ""), {}

        r = self._create_with_retry(messages)
        u = r.usage
        usage = {
            "input_tokens": u.prompt_tokens,
            "output_tokens": u.completion_tokens,
            "total_tokens": u.total_tokens,
        } if u else {}
        return r.choices[0].message.content or "", usage

    def stream(self, messages: list[dict]) -> Iterator[str]:
        if self.mock:
            text, _ = self.complete(messages)
            for w in text.split(" "):
                yield w + " "
            return

        r = self.client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_OUTPUT_TOKENS,
            stream=True,
        )
        for ch in r:
            if ch.choices and ch.choices[0].delta and ch.choices[0].delta.content:
                yield ch.choices[0].delta.content
