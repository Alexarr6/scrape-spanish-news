from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalTag:
    code: str
    display_name: str
    group: str
    description: str
    sort_order: int


CANONICAL_TAGS: tuple[CanonicalTag, ...] = (
    CanonicalTag(
        "politics_national",
        "Politics / National",
        "politics",
        "National politics and party competition",
        10,
    ),
    CanonicalTag(
        "politics_regional",
        "Politics / Regional",
        "politics",
        "Regional politics and autonomous communities",
        20,
    ),
    CanonicalTag(
        "politics_local",
        "Politics / Local",
        "politics",
        "Local government and municipal politics",
        30,
    ),
    CanonicalTag(
        "government", "Government", "politics", "Government actions and executive branch", 40
    ),
    CanonicalTag(
        "parliament",
        "Parliament",
        "politics",
        "Legislative chambers and parliamentary activity",
        50,
    ),
    CanonicalTag(
        "justice", "Justice", "politics", "Courts, judiciary, prosecutors and legal process", 60
    ),
    CanonicalTag("elections", "Elections", "politics", "Elections, campaigns and voting", 70),
    CanonicalTag(
        "public_policy",
        "Public policy",
        "politics",
        "Policy proposals and public administration",
        80,
    ),
    CanonicalTag(
        "corruption",
        "Corruption",
        "politics",
        "Corruption allegations and anti-corruption cases",
        90,
    ),
    CanonicalTag(
        "protest_social_movement",
        "Protest / Social movement",
        "politics",
        "Demonstrations, strikes and civic mobilization",
        100,
    ),
    CanonicalTag(
        "economy_macro",
        "Economy / Macro",
        "economy",
        "Macro economy, GDP, inflation and growth",
        110,
    ),
    CanonicalTag(
        "business_corporate",
        "Business / Corporate",
        "economy",
        "Corporate results, mergers and strategy",
        120,
    ),
    CanonicalTag("housing", "Housing", "economy", "Housing market, rents and home policy", 130),
    CanonicalTag("energy", "Energy", "economy", "Energy policy, utilities and markets", 140),
    CanonicalTag(
        "transport", "Transport", "economy", "Mobility, logistics, rail, air and roads", 150
    ),
    CanonicalTag(
        "labour_employment",
        "Labour / Employment",
        "economy",
        "Jobs, unions, labour disputes and unemployment",
        160,
    ),
    CanonicalTag("health", "Health", "society", "Healthcare, hospitals and public health", 170),
    CanonicalTag(
        "education", "Education", "society", "Schools, universities and education policy", 180
    ),
    CanonicalTag("migration", "Migration", "society", "Migration, asylum and border issues", 190),
    CanonicalTag(
        "security_crime", "Security / Crime", "society", "Crime, policing and public security", 200
    ),
    CanonicalTag(
        "environment", "Environment", "society", "Environment, biodiversity and pollution", 210
    ),
    CanonicalTag("climate", "Climate", "society", "Climate change and climate response", 220),
    CanonicalTag(
        "technology", "Technology", "society", "Technology, internet and digital policy", 230
    ),
    CanonicalTag(
        "media_information",
        "Media / Information",
        "society",
        "Media, journalism, misinformation and platforms",
        240,
    ),
    CanonicalTag("culture", "Culture", "society", "Culture and cultural policy", 250),
    CanonicalTag("sports", "Sports", "society", "Sports and competitions", 260),
    CanonicalTag(
        "international_eu",
        "International / EU",
        "international",
        "European Union institutions and policy",
        270,
    ),
    CanonicalTag(
        "international_diplomacy",
        "International / Diplomacy",
        "international",
        "Diplomacy and bilateral or multilateral relations",
        280,
    ),
    CanonicalTag(
        "war_conflict", "War / Conflict", "international", "Wars, invasions and armed conflict", 290
    ),
    CanonicalTag(
        "defense", "Defense", "international", "Defense policy and military activity", 300
    ),
    CanonicalTag(
        "humanitarian", "Humanitarian", "international", "Humanitarian crises and aid", 310
    ),
    CanonicalTag("legislation", "Legislation", "story_form", "Bills, laws and legal reforms", 320),
    CanonicalTag(
        "court_case", "Court case", "story_form", "Court cases and legal proceedings", 330
    ),
    CanonicalTag(
        "investigation",
        "Investigation",
        "story_form",
        "Investigations by prosecutors, police or watchdogs",
        340,
    ),
    CanonicalTag("scandal", "Scandal", "story_form", "Political or institutional scandal", 350),
    CanonicalTag(
        "agreement_negotiation",
        "Agreement / Negotiation",
        "story_form",
        "Negotiations, pacts and agreements",
        360,
    ),
    CanonicalTag(
        "accident_disaster",
        "Accident / Disaster",
        "story_form",
        "Accidents, disasters and emergencies",
        370,
    ),
    CanonicalTag(
        "election_campaign",
        "Election campaign",
        "story_form",
        "Campaign messaging and campaign trail",
        380,
    ),
    CanonicalTag(
        "statement_reaction",
        "Statement / Reaction",
        "story_form",
        "Statements, responses and political reactions",
        390,
    ),
    CanonicalTag(
        "policy_announcement",
        "Policy announcement",
        "story_form",
        "Announcements of public measures or plans",
        400,
    ),
    CanonicalTag(
        "data_report",
        "Data report",
        "story_form",
        "Surveys, reports and official data releases",
        410,
    ),
)

TAG_BY_CODE = {tag.code: tag for tag in CANONICAL_TAGS}

SOURCE_TAG_MAP = {
    "politica": "politics_national",
    "política": "politics_national",
    "espana": "politics_national",
    "españa": "politics_national",
    "catalunya": "politics_regional",
    "cataluña": "politics_regional",
    "economia": "economy_macro",
    "economía": "economy_macro",
    "empresa": "business_corporate",
    "justicia": "justice",
    "tribunales": "justice",
    "salud": "health",
    "sanidad": "health",
    "educacion": "education",
    "educación": "education",
    "medio ambiente": "environment",
    "clima": "climate",
    "tecnologia": "technology",
    "tecnología": "technology",
    "internacional": "international_diplomacy",
    "ue": "international_eu",
    "europa": "international_eu",
    "deportes": "sports",
}


def validate_tag_codes(tag_codes: list[str]) -> list[str]:
    canonical: list[str] = []
    seen: set[str] = set()
    for code in tag_codes:
        if code not in TAG_BY_CODE:
            raise ValueError(f"Unknown canonical tag: {code}")
        if code in seen:
            continue
        seen.add(code)
        canonical.append(code)
    return canonical
