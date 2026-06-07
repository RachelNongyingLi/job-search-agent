from __future__ import annotations

import re

from .models import CandidateProfile, JobAnalysis, NegativeSignal


MANDATORY_INTERNSHIP_PATTERNS = [
    r"\bmandatory internship\b",
    r"\bcompulsory internship\b",
    r"\bobligatory internship\b",
    r"\bpflicht[- ]?praktikum\b",
    r"\bproof of (a )?(mandatory|compulsory|obligatory) internship\b",
    r"\b(mandatory|compulsory|obligatory).{0,40}\binternship.{0,40}\b(proof|certificate|confirmation)\b",
    r"\b(proof|certificate|confirmation).{0,40}\b(mandatory|compulsory|obligatory).{0,40}\binternship\b",
]

HARD_LOCATION_PATTERNS = [
    r"\blocal candidates? only\b",
    r"\bmust be (based|located|resident|living) in\b",
    r"\bmust live within\b",
    r"\bcommutable distance\b",
    r"\b(onsite|on-site|hybrid|office presence).{0,50}\b(required|mandatory|must|expected)\b",
    r"\b(required|mandatory|must|expected).{0,50}\b(onsite|on-site|hybrid|commut|relocat|local candidate|office)\b",
]

COMMUTE_BLOCKERS = [
    "too far",
    "far away",
    "cannot commute",
    "can't commute",
    "not able to commute",
    "not willing to commute",
    "not willing to relocate",
    "outside commute",
    "cannot relocate",
    "can't relocate",
    "no relocation",
    "not relocate",
    "remote only",
    "unavailable",
]

UNRELATED_REQUIREMENT_GROUPS = {
    "embedded_firmware_hardware": {
        "label": "embedded, firmware, or hardware engineering",
        "terms": [
            "embedded",
            "firmware",
            "microcontroller",
            "pcb",
            "hardware design",
            "fpga",
            "vhdl",
            "verilog",
        ],
    },
    "frontend_mobile_product": {
        "label": "frontend, mobile, or product UI engineering",
        "terms": [
            "react",
            "vue",
            "angular",
            "frontend",
            "front-end",
            "ios",
            "android",
            "swift",
            "kotlin",
            "ui/ux",
        ],
    },
    "enterprise_platform_admin": {
        "label": "enterprise platform administration",
        "terms": [
            "salesforce",
            "servicenow",
            "sap abap",
            "sap basis",
            "dynamics 365",
            "workday",
        ],
    },
    "regulated_professional_credential": {
        "label": "regulated professional credential",
        "terms": [
            "security clearance",
            "licensed attorney",
            "bar admission",
            "clinical license",
            "medical license",
            "certified accountant",
        ],
    },
}

HARD_REQUIREMENT_MARKERS = [
    "must",
    "required",
    "mandatory",
    "proven",
    "hands-on",
    "strong experience",
    "minimum",
    "at least",
    "you have",
    "you bring",
]


def detect_negative_signals(
    profile: CandidateProfile,
    job: JobAnalysis,
    root_matches: list[str],
    upskill_matches: list[str],
) -> list[NegativeSignal]:
    raw = _normalize(job.raw_text)
    facts = profile.market_facts or {}
    evidence_terms = set(profile.all_keywords)
    signals: list[NegativeSignal] = []

    if _matches_any(raw, MANDATORY_INTERNSHIP_PATTERNS) and not _fact_confirmed(
        facts,
        [
            "mandatory_internship_proof",
            "internship_eligibility",
            "student_status",
            "enrollment_status",
        ],
    ):
        signals.append(
            NegativeSignal(
                code="mandatory_internship_unverified",
                severity="block",
                category="eligibility",
                message=(
                    "The JD appears to require proof of a mandatory or compulsory internship, "
                    "but the profile has no confirmed local proof."
                ),
                evidence_required=(
                    "Private local confirmation such as a university mandatory-internship rule, "
                    "enrollment proof, or internship eligibility note."
                ),
                suggested_action=(
                    "Verify this before tailoring. Do not imply mandatory-internship eligibility "
                    "in a resume, cover letter, or recruiter message."
                ),
                score_cap=35,
            )
        )

    if _matches_any(raw, HARD_LOCATION_PATTERNS):
        commute_text = _fact_text(facts, ["commute_or_relocation", "relocation", "location_status"])
        if any(marker in commute_text for marker in COMMUTE_BLOCKERS):
            signals.append(
                NegativeSignal(
                    code="commute_or_location_blocked",
                    severity="block",
                    category="location",
                    message=(
                        "The JD uses hard onsite/local/commute language, and the local profile "
                        "indicates the commute or relocation condition is blocked."
                    ),
                    evidence_required="A private local commute or relocation confirmation.",
                    suggested_action=(
                        "Skip or ask the recruiter before spending time on tailoring. Do not let "
                        "technical overlap hide the location blocker."
                    ),
                    score_cap=35,
                )
            )
        elif not _fact_confirmed(facts, ["commute_or_relocation", "relocation", "location_status"]):
            signals.append(
                NegativeSignal(
                    code="commute_or_location_unverified",
                    severity="verify",
                    category="location",
                    message=(
                        "The JD uses hard onsite/local/commute language, but the profile has no "
                        "confirmed local commute or relocation fact."
                    ),
                    evidence_required="Private confirmation that the office location, commute, or relocation is feasible.",
                    suggested_action=(
                        "Confirm location feasibility before deep tailoring. Keep private address "
                        "or commute details out of public reports."
                    ),
                    score_cap=58,
                )
            )

    unsupported_domains = _unsupported_required_domains(raw, evidence_terms)
    if unsupported_domains:
        cap = 45 if len(root_matches) <= 1 else 55
        signals.append(
            NegativeSignal(
                code="unsupported_project_reframe",
                severity="block",
                category="claim_safety",
                message=(
                    "The JD has hard requirements in an unsupported domain: "
                    f"{', '.join(unsupported_domains)}."
                ),
                evidence_required=(
                    "Direct project, coursework, work, or credential evidence for the required domain."
                ),
                suggested_action=(
                    "Do not rewrite existing projects into this domain. Treat it as a gap, skip, "
                    "or prepare an honest upskill plan."
                ),
                score_cap=cap,
            )
        )

    if _technical_overlap_without_roots(root_matches, upskill_matches, raw, evidence_terms):
        signals.append(
            NegativeSignal(
                code="keyword_overlap_without_root_evidence",
                severity="verify",
                category="claim_safety",
                message=(
                    "The JD can look similar through broad keywords, but no root-strength evidence "
                    "supports the hard requirement cluster."
                ),
                evidence_required="A profile evidence item that can be explained under interview follow-up.",
                suggested_action=(
                    "Keep the score conservative and put this in gaps/upskill instead of resume claims."
                ),
                score_cap=62,
            )
        )

    return _dedupe_signals(signals)


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _fact_confirmed(facts: dict, keys: list[str]) -> bool:
    text = _fact_text(facts, keys)
    if not text:
        return False
    blockers = [
        "keep private",
        "ask locally",
        "unknown",
        "unverified",
        "not verified",
        "unconfirmed",
        "do not publish",
        "not available",
        "cannot",
        "can't",
        " no ",
    ]
    if any(marker in f" {text} " for marker in blockers):
        return False
    confirmations = [
        "yes",
        "confirmed",
        "verified",
        "available",
        "can provide",
        "eligible",
        "enrolled",
        "matriculated",
        "local",
        "within commute",
        "commutable",
        "willing to relocate",
        "mandatory internship",
        "pflichtpraktikum",
    ]
    return any(marker in text for marker in confirmations)


def _fact_text(facts: dict, keys: list[str]) -> str:
    values: list[str] = []
    for key in keys:
        value = facts.get(key, "")
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            values.extend(str(item) for item in value.values())
        else:
            values.append(str(value))
    return _normalize(" ".join(values))


def _unsupported_required_domains(text: str, evidence_terms: set[str]) -> list[str]:
    unsupported: list[str] = []
    for group in UNRELATED_REQUIREMENT_GROUPS.values():
        terms = list(group["terms"])
        present = [term for term in terms if term in text]
        if present and _hard_required(text, present) and not _has_support(present, evidence_terms):
            unsupported.append(str(group["label"]))
    return unsupported


def _hard_required(text: str, terms: list[str]) -> bool:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for sentence in sentences:
        if any(term in sentence for term in terms) and any(marker in sentence for marker in HARD_REQUIREMENT_MARKERS):
            return True
    return False


def _has_support(terms: list[str], evidence_terms: set[str]) -> bool:
    return any(term in evidence_terms for term in terms)


def _technical_overlap_without_roots(
    root_matches: list[str],
    upskill_matches: list[str],
    text: str,
    evidence_terms: set[str],
) -> bool:
    if root_matches or not upskill_matches:
        return False
    hard_skill_mentions = [
        "production",
        "deployment",
        "cloud",
        "dashboard",
        "monitoring",
        "rpa",
    ]
    mentioned = [term for term in hard_skill_mentions if term in text]
    return bool(mentioned and not _has_support(mentioned, evidence_terms))


def _dedupe_signals(signals: list[NegativeSignal]) -> list[NegativeSignal]:
    seen = set()
    deduped = []
    for signal in signals:
        if signal.code in seen:
            continue
        seen.add(signal.code)
        deduped.append(signal)
    return deduped


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()
