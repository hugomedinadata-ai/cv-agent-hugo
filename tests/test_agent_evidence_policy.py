from app.agent import SYSTEM_PROMPT


def test_agent_distinguishes_direct_work_from_technical_coordination():
    assert "IMPLEMENTACIÓN DIRECTA" in SYSTEM_PROMPT
    assert "LIDERAZGO / COORDINACIÓN TÉCNICA" in SYSTEM_PROMPT
    assert "Hugo NO utilizó Ab Initio directamente" in SYSTEM_PROMPT
    assert "no la tiene" in SYSTEM_PROMPT


def test_agent_does_not_claim_production_ml_or_genai_model_delivery():
    assert "No afirmes que Hugo desarrolló, entrenó, desplegó o puso modelos" in SYSTEM_PROMPT
    assert "experiencia productiva en ingeniería de datos" in SYSTEM_PROMPT


def test_agent_separates_documented_experience_from_proposals():
    assert "Experiencia documentada:" in SYSTEM_PROMPT
    assert "Propuesta técnica:" in SYSTEM_PROMPT
    assert "no un proyecto que ya implementó" in SYSTEM_PROMPT


def test_agent_response_depth_is_adaptive_and_not_artificially_short():
    assert "suficientemente profundas" in SYSTEM_PROMPT
    assert "sin limitarte artificialmente a 2-5 oraciones" in SYSTEM_PROMPT


def test_agent_keeps_project_metrics_attached_to_the_correct_employer():
    assert "Citibanamex: más de 12 millones de registros diarios" in SYSTEM_PROMPT
    assert "Banco Azteca/Grupo Salinas: 90% menos esfuerzo manual" in SYSTEM_PROMPT
    assert "BBVA: automatización de reportes" in SYSTEM_PROMPT


def test_agent_describes_devops_and_cicd_as_coordination_when_that_is_the_evidence():
    assert "coordinó y gobernó las liberaciones bajo prácticas DevOps y CI/CD" in SYSTEM_PROMPT
    assert "No afirmes que Hugo diseñó, programó o implementó personalmente" in SYSTEM_PROMPT


def test_agent_includes_documented_leadership_and_management_scope():
    assert "backlog, épicas e historias para hasta tres equipos" in SYSTEM_PROMPT
    assert "sprints de cuatro semanas" in SYSTEM_PROMPT
    assert "presupuesto y gestión de proveedores" in SYSTEM_PROMPT


def test_agent_separates_personal_genai_project_from_enterprise_production():
    assert "proyecto práctico personal" in SYSTEM_PROMPT
    assert "nunca como solución empresarial desplegada para un empleador" in SYSTEM_PROMPT