# Agente de CV de Hugo Medina

Agente conversacional que responde preguntas sobre la trayectoria profesional de Hugo Medina
(experiencia, habilidades y proyectos). Expone `POST /v1/responses` con un subconjunto del contrato
Open Responses y streaming SSE. **No se declara conformidad completa:** consulta las diferencias
conocidas y ejecuta las pruebas oficiales antes de afirmar compatibilidad total.

## Arquitectura

```
Pregunta ──► Guardrails de entrada ──► Recuperación (BM25 sobre el CV) ──► Prompt con reglas
             (inyección, longitud)       top-k secciones + resumen          + contexto + historial
                                                                                  │
Respuesta ◄── Verificación de salida ◄── LLM (API compatible con OpenAI) ◄────────┘
              (cifras no respaldadas,      Gemini / Groq / OpenRouter / Azure OpenAI
               fuentes y latencia en metadata)
```

| Componente | Archivo | Qué hace |
|---|---|---|
| Base de conocimiento | `knowledge/*.md` | El CV en Markdown, una sección por tema (`## Título`). Es la única fuente de verdad. |
| Recuperación | `app/retriever.py` | BM25 con normalización de acentos, stopwords y sinónimos; siempre agrega el resumen. |
| Guardrails | `app/guardrails.py` | Detección de prompt injection y verificación de cifras contra el CV. |
| Orquestación | `app/agent.py` | Arma el prompt con reglas de honestidad y llama al modelo. |
| Modelo | `app/llm.py` | Cliente compatible con OpenAI: se cambia de proveedor solo con variables de entorno. |
| Protocolo | `app/openresponses.py`, `app/main.py` | Request/response y eventos SSE de Open Responses, `previous_response_id`, errores tipados. |
| Pruebas | `tests/` | Pruebas de contrato con modelo simulado (corren en GitHub Actions). |
| Evaluación | `evals/` | 19 casos: exactitud, honestidad, seguridad, cifras no respaldadas y latencia. |

## Decisiones técnicas y por qué

1. **BM25 en lugar de una base vectorial.** El CV tiene ~15 secciones. Una base vectorial añade
   costo, latencia y una dependencia más sin mejorar la calidad a este tamaño. BM25 es determinista
   y explicable (se ve qué sección se usó). Si el corpus creciera, el siguiente paso es búsqueda
   híbrida (BM25 + embeddings) con reranking.
2. **Fragmentación por sección del CV.** Cada `##` es una unidad con sentido completo (un rol, un
   logro), así el contexto recuperado no corta ideas a la mitad.
3. **Modelo intercambiable.** El cliente usa la interfaz compatible con OpenAI que ofrecen Gemini,
   Groq, OpenRouter y Azure OpenAI. Cambiar de proveedor es cambiar `LLM_BASE_URL` y `LLM_MODEL`.
   Temperatura 0.2 para respuestas consistentes.
4. **Honestidad antes que impresionar.** El prompt obliga a responder solo con el CV, a decir
   cuando algo no está y a aclarar lo que se conoce solo por cursos. El agente reconoce que Hugo
   todavía no ha puesto en producción IA generativa para un empleador.
5. **Seguridad (OWASP LLM Top 10, nivel básico).** El rol de sistema lo define el servidor (se
   ignoran mensajes `system`/`developer` del cliente), se detecta prompt injection, se limita el
   tamaño de entrada y el CV no incluye datos privados (el teléfono no está en la base).
6. **Verificación de salida.** Cada respuesta revisa si contiene cifras que no existen en el CV
   (`ungrounded_numbers` en `metadata`): es una señal barata de alucinación que queda en los logs.
7. **Límite de uso.** Máximo 30 solicitudes por minuto por IP (configurable con `RATE_LIMIT_PER_MIN`), con error 429 tipado.
8. **Observabilidad.** Cada respuesta registra fuentes usadas, latencia y tokens en logs JSON, y
   devuelve fuentes y latencia en `metadata`.
9. **Despliegue serverless.** Vercel (o cualquier contenedor con el `Dockerfile`). Sin servidores
   que administrar; las llaves viven en variables de entorno, nunca en el código.

## Correr en local

```bash
pip install -r requirements.txt
cp .env.example .env   # agrega tu LLM_API_KEY
export $(cat .env | xargs) && uvicorn app.main:app --reload
curl -s localhost:8000/v1/responses -H "Content-Type: application/json" \
  -d '{"model":"hugo-cv-agent","input":"¿Cuál es el logro principal de Hugo?"}'
```

Pruebas sin llave: `LLM_PROVIDER=mock python -m pytest -q tests`

## Evaluación

```bash
pip install -r evals/requirements.txt
python evals/run_evals.py https://<tu-dominio>.vercel.app [AGENT_API_KEY]
```

## Compatibilidad con Open Responses

Las pruebas de `tests/` validan el contrato (objeto `response`, items `message`/`output_text`, eventos SSE en orden con `sequence_number`, errores tipados y `previous_response_id`). Después de desplegar, se valida además con las pruebas de aceptación oficiales en https://www.openresponses.org/compliance.

## Limitaciones conocidas y siguientes pasos

- La memoria de `previous_response_id` vive en memoria del proceso: en serverless puede perderse
  entre invocaciones. Siguiente paso: guardarla en Redis o Postgres con expiración.
- La detección de inyección es por patrones; el siguiente paso es un clasificador dedicado.
- Siguiente paso de evaluación: LLM-as-judge para groundedness con Ragas o DeepEval.

---
Construido por Hugo Medina con apoyo de asistentes de IA para programar, como parte del Reto IA Banorte.
