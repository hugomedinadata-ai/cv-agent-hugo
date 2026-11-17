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


def test_agent_uses_star_and_evidence_based_technical_interview_answers():
    assert "resultado (STAR)" in SYSTEM_PROMPT
    assert "trade-offs únicamente cuando estén documentados" in SYSTEM_PROMPT



def test_agent_does_not_claim_personal_cicd_tool_implementation():
    assert "no demuestra configuración o uso hands-on por Hugo" in SYSTEM_PROMPT
    assert "Control-M o Airflow como herramientas CI/CD" in SYSTEM_PROMPT
    assert "AWS CloudFormation debe describirse como aprovisionamiento de infraestructura" in SYSTEM_PROMPT
    assert "No atribuyas causalidad exclusiva a CI/CD" in SYSTEM_PROMPT


def test_agent_does_not_invent_linear_mlops_cloudera_sequence():
    assert "No afirmes que los modelos o scores se almacenaban primero en Cloudera" in SYSTEM_PROMPT
    assert "ni que todos los flujos seguían una secuencia lineal única" in SYSTEM_PROMPT


def test_agent_separates_aws_kafka_initiatives_from_mlops_pipeline():
    assert "no las presentes automáticamente como etapas del mismo pipeline MLOps" in SYSTEM_PROMPT


def test_agent_explicitly_qualifies_bbva_aws_timeline_and_catalog_causality():
    assert "la cronología exacta no está confirmada" in SYSTEM_PROMPT
    assert "no está confirmada la relación causal exacta" in SYSTEM_PROMPT
    assert "No afirmes que los catálogos causaron por sí solos" in SYSTEM_PROMPT


def test_agent_does_not_invent_a_single_physical_mlops_data_flow():
    assert "no afirmes que los scores generados por MLOps necesariamente ingresaban primero a Cloudera" in SYSTEM_PROMPT
    assert "separa los flujos de datos de entrada para analítica/modelos" in SYSTEM_PROMPT


def test_agent_uses_formal_citibanamex_title_without_overstating_manager_title():
    assert "el título formal de Hugo era Lead Tech" in SYSTEM_PROMPT
    assert "no presentar Senior Data & Analytics Manager como título contractual confirmado" in SYSTEM_PROMPT


def test_agent_preserves_group_salinas_bi_depth():
    assert "Business Intelligence Lead" in SYSTEM_PROMPT
    assert "Murex" in SYSTEM_PROMPT
    assert "Power BI, QlikView y SAS" in SYSTEM_PROMPT


def test_agent_does_not_infer_git_jenkins_hands_on_from_stack_presence():
    assert "Git y Jenkins aparecen en el stack/entorno documentado" in SYSTEM_PROMPT
    assert "no demuestra configuración, desarrollo o uso hands-on por Hugo" in SYSTEM_PROMPT
