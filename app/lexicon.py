"""Roman Urdu and Urdu health-domain vocabulary for interpretation safeguards."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DomainTerm:
    canonical: str
    variants: tuple[str, ...]
    meanings: tuple[str, ...]
    topic: str
    ambiguous: bool = False


DOMAIN_TERMS = (
    DomainTerm(
        "teeka",
        ("teeka", "tika", "tikka", "teekay", "ٹیکا", "ٹیکہ", "ٹیکے"),
        ("vaccine/immunization", "injection"),
        "vaccination_or_injection",
        True,
    ),
    DomainTerm(
        "vaccine",
        ("vaccine", "vaccines", "vax", "ویکسین", "ٹیکہ کاری", "حفاظتی ٹیکہ"),
        ("vaccine/immunization",),
        "vaccination",
    ),
    DomainTerm(
        "polio",
        ("polio", "polio drops", "پولیو", "پولیو کے قطرے"),
        ("vaccine/immunization",),
        "vaccination",
    ),
    DomainTerm(
        "immunization",
        ("immunization", "immunisation", "vaccination", "حفاظتی ٹیکہ کاری", "حفاظتی ٹیکہ جات"),
        ("vaccine/immunization",),
        "vaccination",
    ),
    DomainTerm(
        "injection",
        ("injection", "inject", "انجیکشن", "زُق", "ٹیکہ لگانا"),
        ("injection",),
        "injection",
    ),
    DomainTerm(
        "medicine",
        ("medicine", "medication", "dawai", "dawa", "دوا", "دوائی", "ادویات"),
        ("medicine",),
        "medication",
    ),
    DomainTerm(
        "tablet",
        ("tablet", "goli", "گولی", "قرص"),
        ("medicine",),
        "medication",
    ),
    DomainTerm(
        "drops",
        ("drops", "qatray", "qatre", "قطرے", "قطرات"),
        ("oral drops", "vaccine/immunization"),
        "vaccination_or_medicine",
        True,
    ),
    DomainTerm(
        "drip",
        ("drip", "saline", "ڈِرپ", "ڈرپ", "نمکول"),
        ("intravenous fluid",),
        "maternal_child_or_general_care",
    ),
    DomainTerm(
        "fever",
        ("bukhar", "fever", "بخار", "تپ"),
        ("fever",),
        "general_health",
    ),
    DomainTerm(
        "pain",
        ("dard", "pain", "درد", "تکلیف"),
        ("pain",),
        "general_health",
    ),
    DomainTerm(
        "pregnancy",
        ("hamal", "pregnancy", "pregnant", "حمل", "حاملہ", "حمل ٹھہرنا"),
        ("pregnancy",),
        "maternal_health",
    ),
    DomainTerm(
        "mother",
        ("maa", "walida", "mother", "ماں", "والدہ"),
        ("mother",),
        "maternal_health",
    ),
    DomainTerm(
        "child",
        ("bacha", "bachay", "child", "children", "بچہ", "بچے", "بچوں"),
        ("child",),
        "child_health",
    ),
    DomainTerm(
        "newborn",
        ("newborn", "nawzaida", "نوزائیدہ", "شیر خوار"),
        ("newborn",),
        "child_health",
    ),
    DomainTerm(
        "breastfeeding",
        ("breastfeeding", "doodh pilana", "doodh pilai", "دودھ پلانا", "رضاعت"),
        ("breastfeeding",),
        "maternal_child_health",
    ),
    DomainTerm(
        "birth",
        ("delivery", "paidaish", "wiladat", "زچگی", "پیدائش", "ولادت"),
        ("delivery",),
        "maternal_health",
    ),
    DomainTerm(
        "family_planning",
        ("family planning", "bachon mein waqfa", "منصوبہ بندی", "بچوں میں وقفہ"),
        ("family planning",),
        "maternal_health",
    ),
    DomainTerm(
        "diarrhea",
        ("dast", "diarrhea", "ishal", "دست", "اسہال"),
        ("diarrhea",),
        "child_health",
    ),
    DomainTerm(
        "malnutrition",
        ("kamzori", "malnutrition", "ghizai kami", "کمزوری", "غذائی کمی"),
        ("malnutrition",),
        "child_health",
    ),
    DomainTerm(
        "lady_health_worker",
        ("lhw", "lady health worker", "health worker", "لیڈی ہیلتھ ورکر", "صحت کارکن"),
        ("community health worker",),
        "community_health",
    ),
)

_VARIANT_TO_TERM = {
    variant.casefold(): term
    for term in DOMAIN_TERMS
    for variant in term.variants
}


def _contains_variant(text: str, variant: str) -> bool:
    if re.search(r"[A-Za-z]", variant):
        return bool(re.search(rf"(?<![A-Za-z]){re.escape(variant)}(?![A-Za-z])", text, re.IGNORECASE))
    return variant in text


def detect_domain_terms(text: str) -> list[DomainTerm]:
    """Return distinct domain terms found in Urdu or Roman Urdu text."""
    return [
        term
        for term in DOMAIN_TERMS
        if any(_contains_variant(text, variant) for variant in term.variants)
    ]


def interpret_claim(text: str) -> dict:
    """Build a deterministic interpretation used to constrain retrieval."""
    terms = detect_domain_terms(text)
    meanings = sorted({meaning for term in terms for meaning in term.meanings})
    explicit_topics = {
        term.topic
        for term in terms
        if not term.ambiguous and term.topic in {"vaccination", "injection"}
    }
    if re.search(
        r"(dard\s+ka|pain\s+ka|درد\s+کا).{0,12}(teeka|tika|tikka|ٹیکا|ٹیکہ)",
        text,
        re.IGNORECASE,
    ):
        explicit_topics.add("injection")
    ambiguous_terms = [term.canonical for term in terms if term.ambiguous]

    if ambiguous_terms and not explicit_topics:
        topic = "ambiguous"
    elif "vaccination" in explicit_topics:
        topic = "vaccination"
    elif "injection" in explicit_topics:
        topic = "injection"
    elif explicit_topics:
        topic = sorted(explicit_topics)[0]
    else:
        topic = "general_health"

    return {
        "matched_terms": [term.canonical for term in terms],
        "possible_meanings": meanings,
        "ambiguous_terms": ambiguous_terms,
        "topic": topic,
        "ambiguity_detected": bool(ambiguous_terms and not explicit_topics),
    }
