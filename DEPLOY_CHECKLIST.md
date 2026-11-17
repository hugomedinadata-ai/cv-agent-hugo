# Checklist de despliegue — cv-agent-hugo

## Antes de publicar
- [ ] Confirmar que el repositorio será público.
- [ ] Verificar que `.env`, claves y tokens no estén en Git.
- [ ] Confirmar en Google AI Studio el identificador vigente del modelo Gemini.
- [ ] Preparar `LLM_API_KEY` como secreto de Vercel.
- [ ] Generar un `AGENT_API_KEY` aleatorio y guardarlo como secreto de Vercel.
- [ ] Configurar `CORS_ORIGINS` con el origen exacto del frontend (sin comodines).
- [ ] Configurar `REDIS_URL` para sesiones y rate limiting compartidos entre instancias.
- [ ] Configurar `SESSION_TTL_SECONDS` (por defecto 3600 segundos).
- [ ] Configurar `RATE_WINDOW_SECONDS` y `RATE_LIMIT_PER_MIN` según el tráfico esperado.
- [ ] Activar `TRUST_PROXY_HEADERS=true` solo después de confirmar que el hosting sobrescribe `x-real-ip` y no acepta suplantación desde el cliente.
- [ ] Configurar `LLM_PROVIDER=openai_compatible`.
- [ ] Confirmar `LLM_BASE_URL` y `LLM_MODEL`.
- [ ] No activar `LLM_PROVIDER=mock` en producción.

## Después del despliegue
- [ ] Abrir `/health` y confirmar HTTP 200.
- [ ] Enviar una solicitud real a `/v1/responses` con Bearer.
- [ ] Confirmar que la respuesta está fundamentada en `knowledge/*.md`.
- [ ] Probar una pregunta fuera del CV y una pregunta de inyección.
- [ ] Probar `stream=true` y revisar los eventos SSE.
- [ ] Ejecutar `evals/run_evals.py` contra la URL desplegada.
- [ ] Probar el registro del endpoint en Banorte.
- [ ] Registrar resultados y limitaciones reales en README.

## Variables de entorno
- `LLM_API_KEY` (secreto obligatorio para Gemini real)
- `LLM_BASE_URL` (opcional; valor por defecto apunta al endpoint OpenAI-compatible de Gemini)
- `LLM_MODEL` (confirmar modelo disponible en AI Studio)
- `LLM_PROVIDER=openai_compatible`
- `AGENT_API_KEY` (secreto obligatorio; compartir solo mediante el mecanismo seguro de la plataforma cliente)
- `CORS_ORIGINS` (orígenes exactos del frontend, separados por comas)
- `REDIS_URL` (recomendado/obligatorio para despliegues multi-instancia; habilita sesiones y rate limiting compartidos)
- `SESSION_TTL_SECONDS` (TTL del historial; default 3600)
- `RATE_LIMIT_PER_MIN` (default 30 solicitudes por ventana)
- `RATE_WINDOW_SECONDS` (default 60 segundos)
- `TRUST_PROXY_HEADERS` (default false; solo true tras validar proxy confiable)


Sin `REDIS_URL`, las sesiones y el rate limit usan memoria local y no se comparten entre instancias. En producción multi-instancia, no desplegar sin Redis. El cliente Redis falla en modo cerrado cuando está configurado pero no disponible.

Nunca incluir valores de secretos en GitHub, capturas, logs o mensajes de chat.
