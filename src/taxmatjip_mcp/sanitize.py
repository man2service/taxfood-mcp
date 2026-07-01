"""Conservative PII redaction applied to free-text fields (purpose, sourceTitle)
before they leave the server.

The dataset is department-level (institution/department are official org units, not
people) and already near-clean, but a handful of disclosure rows carry an incidental
personal name followed by a job title (e.g. "홍길동 과장" or "홍길동(과장)"). We redact
the NAME token only, and only when it is a 2-4 syllable Hangul run separated from the
title by whitespace or a bracket — so an org-unit name like "총무과장" (no separator)
is never touched. An org-suffix denylist keeps phrases like "협의회 회장" intact.
Favours no-leak safety while avoiding obvious false positives.
"""

from __future__ import annotations

import re

# Job titles that follow a personal name. Broad by design (recall favours no-leak).
_TITLES = (
    "부총장", "본부장", "센터장", "사업단장", "단장", "실장", "국장", "과장", "팀장",
    "부장", "차장", "처장", "청장", "관장", "원장", "소장", "사무관", "주무관",
    "서기관", "주사", "계장", "반장", "위원장", "대표", "회장", "이사", "감사",
)

# If the matched "name" actually ends with one of these, it is an organisation, not a
# person — leave it intact (e.g. "협의회 회장", "추진단 단장").
_ORG_SUFFIXES = (
    "위원회", "협의회", "추진단", "지원단", "운영위", "이사회", "대책위", "실무단",
    "자문단", "총회", "협회", "조합", "재단", "법인", "본부", "센터", "사업단",
    "추진위", "심의회", "연합회", "봉사단", "간담회", "학교", "대학교",
)

_REDACTED = "ㅇㅇㅇ"
# name (2-4 Hangul, at a word boundary) + a REQUIRED separator (space or bracket) + title.
_SEP = r"(?:\s+|\s*[(（]\s*)"
_NAME_TITLE = re.compile(
    r"(?<![가-힣])([가-힣]{2,4})" + _SEP + r"(?:" + "|".join(_TITLES) + r")"
)


def _redact(match: re.Match[str]) -> str:
    name = match.group(1)
    if any(name.endswith(suffix) for suffix in _ORG_SUFFIXES):
        return match.group(0)  # organisation, not a person — leave intact
    return match.group(0).replace(name, _REDACTED, 1)


def scrub_text(text: str) -> str:
    """Redact incidental 'name + title' PII, leaving org-unit names intact."""
    if not text:
        return text
    return _NAME_TITLE.sub(_redact, text)
