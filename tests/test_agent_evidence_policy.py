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
