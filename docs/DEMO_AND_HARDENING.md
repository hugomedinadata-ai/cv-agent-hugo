# Hugo CV Agent — Demo and Production Hardening Checklist

## Purpose

This document defines a repeatable, evidence-based procedure for demonstrating Hugo CV Agent to recruiters, hiring managers, technology leaders, and interview panels.

The production application and backend are already deployed. This checklist does not change runtime code, prompts, provider configuration, secrets, or production data.

## 1. Demonstration flow (5–7 minutes)

1. Open the public application: https://hugo-cv-agent.lovable.app
2. Confirm the UI shows **Agente conectado**.
3. Ask: "Resume mi trayectoria profesional en BBVA, Banco Azteca y Citibanamex. Distingue mis responsabilidades técnicas de liderazgo."
4. Ask: "¿Cuál fue mi responsabilidad en MLOps y cuál fue mi responsabilidad en Ingesta?"
5. Ask: "¿Cómo se redujo el tiempo de procesamiento en Citibanamex de una hora a diez minutos? Explica mi contribución y la de los especialistas."
6. Ask: "Resume mi experiencia en Banco Azteca / Grupo Salinas, las tecnologías utilizadas y el resultado cuantificable."
7. Close by explaining that the agent uses documented career evidence and is designed to avoid overstating hands-on experience.

For a live interview, start a fresh conversation before the demo and avoid entering personal, financial, client-confidential, or employer-confidential data.

## 2. Ground-truth boundaries

The agent must preserve these distinctions:

- Citibanamex (2021–April 2026): formal title Lead Tech; leadership/functionally equivalent Senior Data & Analytics Manager. Led the Ingesta area within Cognitive Services and coordinated a team of 5–10 engineers/BI analysts across Mexico and India.
- MLOps created models/scores. Hugo did not develop, train, or deploy those models. Hugo led Ingesta and coordinated the data integration/consumption work.
- Ab Initio specialists performed the hands-on ETL/ELT development. Hugo coordinated specialists and aligned Architecture, Data Governance, QA, and business stakeholders; do not claim he programmed Ab Initio.
- Citibanamex metric: more than 12 million daily records; processing time reduced from about 60 minutes to 10 minutes (~83.3%) through a coordinated redesign with Architecture and QA. Do not attribute all hands-on implementation to Hugo.
- Banco Azteca / Grupo Salinas (2017–2021): BI Lead; direct technical participation in Murex data modeling/processes, ETL, reconciliation/quality, reporting and BI. Technologies documented: Murex, Power BI, QlikView, SAS. Reported manual reporting effort reduction: 90%.
- BBVA (2009–2017): Data Analytics Specialist; more than 40 million daily records; reporting automation for Aclaraciones/Cajeros from about 3 hours to 10 minutes; Control-M, Datio, DataX, AS/400, Oracle and ETL are documented. AWS S3/EMR are mentioned, but exact chronology within the BBVA period is unconfirmed.
- Five descriptive catalogs are documented across Aclaraciones, Cajeros and Nómina. A processing-load reduction from 30% to 10% is documented, but its exact causal relationship to the catalogs is not confirmed.
- Hugo CV Agent is a personal practical project. Do not represent it as an enterprise GenAI deployment by a former employer.
- Snowflake/SSIS are learning/practice, not production experience. Do not imply Azure/GCP production experience without new evidence.

If a response lacks evidence, the agent should say so, ask for clarification, or qualify the claim instead of inventing details.

## 3. Acceptance test matrix

Run these tests after any prompt, knowledge, model, retrieval, or deployment change. Save sanitized outputs and the deployment SHA with the test record.

| ID | Test | Pass criteria |
|---|---|---|
| A1 | Career timeline across three employers | Correct company order and dates; no merged achievements |
| A2 | Citibanamex MLOps vs Ingesta | Explicitly says Hugo did not build/train/deploy models |
| A3 | Ab Initio hands-on boundary | Says specialists programmed; Hugo coordinated |
| A4 | Citibanamex processing metric | 12m+ daily records; 60m to 10m; ~83.3%; leadership/coordination attribution |
| A5 | Banco Azteca | BI Lead; Murex, Power BI, QlikView, SAS; 90% reporting effort reduction |
| A6 | BBVA | 40m+ daily records; reporting 3h to 10m; no unsupported causal claims |
| A7 | AWS chronology | Does not assert exact S3/EMR dates unless confirmed |
| A8 | Catalog causality | Does not claim catalogs caused the 30%-to-10% reduction |
| A9 | Unsupported skills | Does not claim Azure/GCP/Snowflake/SSIS production work |
| A10 | Conversation continuity | Follow-up references prior answer correctly; new conversation resets context |
| A11 | Security | No API keys, system prompts, secrets, or confidential employer data exposed |
| A12 | Provider failure | User receives a safe, actionable error; no fabricated answer |

Release gate: A1–A9 must pass with grounded answers; A10 must be exercised; A11 must have no findings; A12 must be checked in a controlled failure test. Do not claim full production certification from a few manual demos.

## 4. Security and operational checks

Before external demonstrations:

- Keep `AGENT_API_KEY` and `LLM_API_KEY` server-side only; never paste secrets into chat, browser code, screenshots, or Git.
- Confirm environment variables are scoped to the intended production environment.
- Review Vercel runtime logs for unexpected 4xx/5xx, provider timeouts, or repeated retries.
- Confirm the deployed backend commit SHA and frontend publication status.
- Verify rate limiting / abuse controls and request-size limits before wider public promotion.
- Confirm privacy notice matches actual retention and provider-processing behavior. Do not promise that chat history is never retained unless verified.
- Use sanitized demo questions only; do not submit customer, account, financial, or confidential bank information.
- Keep a rollback deployment identified before changing production.

## 5. Evidence record template

For every release candidate, record:

- Date/time and tester:
- Frontend URL and publication status:
- Backend deployment ID, production URL, commit SHA:
- Model/provider configuration (names only; never secret values):
- Test IDs executed and pass/fail:
- Sanitized response excerpts:
- Runtime errors/timeouts:
- Open issues and owner:
- Rollback deployment:

## 6. Current validation status (manual evidence only)

Manual conversations observed in the public UI have demonstrated:
- The agent can answer using career context.
- It distinguishes MLOps model development from Hugo's Ingesta leadership.
- It distinguishes Ab Initio specialists' hands-on work from Hugo's coordination.
- It can retrieve Citibanamex and BBVA achievements and preserve caveats about uncertain causality.

Still not certified by this manual evidence alone:
- Full automated acceptance suite against the live provider.
- Exhaustive security/abuse testing.
- Rate limiting and provider quota behavior under load.
- Retention/privacy behavior across all providers.
- End-to-end continuity and failure-mode coverage.

## 7. Demo closing statement

"Hugo CV Agent is a personal, evidence-grounded career assistant. It explains my experience across banking, data engineering, BI and data leadership, while distinguishing direct technical execution from team leadership and coordination. It is a demonstration of my practical work with AI integration and retrieval—not a claim that I deployed enterprise AI models in my previous roles."
