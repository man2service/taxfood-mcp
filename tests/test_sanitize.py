from taxmatjip_mcp.sanitize import scrub_text


def test_redacts_name_before_title():
    assert scrub_text("홍길동 과장 주재 간담회") == "ㅇㅇㅇ 과장 주재 간담회"


def test_redacts_name_with_honorific_suffix_title():
    assert scrub_text("김철수 주무관님 참석") == "ㅇㅇㅇ 주무관님 참석"


def test_keeps_org_unit_without_space():
    # "총무과장" is 총무과+장, not a personal name — must stay intact (no space).
    assert scrub_text("총무과장 회의") == "총무과장 회의"


def test_keeps_department_names():
    assert scrub_text("국제교류과 간담회") == "국제교류과 간담회"
    assert scrub_text("도시공간전략과 현장방문") == "도시공간전략과 현장방문"


def test_redacts_compound_surname():
    # 4-syllable name (compound surname 남궁).
    assert scrub_text("남궁철수 과장 주재") == "ㅇㅇㅇ 과장 주재"


def test_redacts_bracket_title_form():
    assert scrub_text("홍길동(과장) 주재 간담회") == "ㅇㅇㅇ(과장) 주재 간담회"


def test_keeps_org_suffix_roles():
    # "협의회 회장", "추진단 단장" are organisations, not people.
    assert scrub_text("협의회 회장 인사말") == "협의회 회장 인사말"
    assert scrub_text("추진단 단장 회의") == "추진단 단장 회의"


def test_empty_and_none_safe():
    assert scrub_text("") == ""
    assert scrub_text("일반적인 목적 텍스트") == "일반적인 목적 텍스트"
