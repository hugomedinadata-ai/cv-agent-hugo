from evals.run_evals import check


def test_refusal_does_not_pass_for_contact_or_profile_mentions_alone():
    case = {"refusal": True}
    assert check(case, "Puedes contactarlo por LinkedIn o correo.") == [
        "no reconoció explícitamente la falta de información o el límite de alcance"
    ]


def test_refusal_passes_when_information_gap_is_explicit():
    case = {"refusal": True}
    assert check(case, "Esa certificación no está documentada en la información disponible.") == []


def test_out_of_scope_refusal_accepts_explicit_scope_boundary():
    case = {"refusal": True, "scope_refusal": True}
    assert check(case, "Solo puedo conversar sobre la trayectoria profesional de Hugo.") == []


def test_scope_boundary_does_not_replace_salary_information_gap():
    case = {"refusal": True}
    assert check(case, "Solo puedo conversar sobre su trayectoria profesional.") == [
        "no reconoció explícitamente la falta de información o el límite de alcance"
    ]
