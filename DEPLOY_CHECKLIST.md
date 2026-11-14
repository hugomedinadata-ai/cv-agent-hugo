# Checklist de despliegue — cv-agent-hugo

## Antes de publicar
- [ ] Confirmar que el repositorio será público.
- [ ] Verificar que `.env`, claves y tokens no estén en Git.
- [ ] Confirmar en Google AI Studio el identificador vigente del modelo Gemini.
- [ ] Preparar `LLM_API_KEY` como secreto de Vercel.
- [ ] Generar un `AGENT_API_KEY` aleatorio y guardarlo como secreto de Vercel.
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
- `AGENT_API_KEY` (secreto recomendado; compartir con Banorte solo por el mecanismo seguro de su plataforma)
- `RATE_LIMIT_PER_MIN` (opcional; límite por instancia, no global)

Nunca incluir valores de secretos en GitHub, capturas, logs o mensajes de chat.
