"""
prompt_templates.py — Production Prompt Template Library

50+ hand-crafted, parameterised prompt templates covering all 6 intent
categories. These serve three purposes:

  1. Guaranteed diversity baseline — even without an LLM, templates produce
     realistic prompts covering every intent type proportionally.

  2. LLM seed context — when live mode is on, templates are injected into
     the GPT system prompt as *examples*, steering the model to produce
     prompts of the same style without repeating the exact same templates.

  3. Fallback on LLM failure — if the OpenAI call times out or returns
     malformed JSON, the template engine fills the gap so the pipeline
     never stalls.

Template syntax:
  All strings use Python str.format() placeholders:
    {brand}       — the target brand name
    {competitor}  — one competitor name (cycling through the list)
    {keyword}     — one keyword (cycling through the list)
    {use_case}    — one use case (cycling through the list)
    {product_line}— one product line (cycling through the list)
    {industry}    — the industry string
    {audience}    — the target audience string
    {geo}         — the first geography string
"""

from models import IntentCategory

# ─────────────────────────────────────────────────────────────────────────────
# Template bank — each category has ~10 templates
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES: dict[IntentCategory, list[str]] = {

    # ── Informational ─────────────────────────────────────────────────────────
    # User wants to learn. No brand loyalty yet. High volume in real AI queries.
    IntentCategory.INFORMATIONAL: [
        "What should I look for when choosing a {product_line} for {use_case}?",
        "Which {industry} brands offer products suited to {use_case}?",
        "What are the main differences between premium and budget {product_line}?",
        "What should {audience} know before buying a {keyword}?",
        "Which {product_line} options are available in {geo}?",
        "What features matter most in a {product_line} for {use_case}?",
        "How can I choose a reliable {keyword} for everyday use?",
        "What are the advantages of foldable devices compared with standard smartphones?",
        "How do I compare battery life, camera quality, and performance in smartphones?",
        "Which products are suitable for {use_case} in the {industry} market?",
    ],

    # ── Comparative ───────────────────────────────────────────────────────────
    # User is evaluating options. Most valuable intent — brand is directly named.
    IntentCategory.COMPARATIVE: [
        "How do {brand} smartphones compare with {competitor} for {use_case}?",
        "{brand} vs {competitor}: which brand offers better {product_line} options?",
        "What are the main differences between {brand} and {competitor} phones?",
        "Compare {brand} and {competitor} on camera, battery life, and performance.",
        "Which is a better choice for {audience}, {brand} or {competitor}?",
        "How do {brand} and {competitor} compare for {use_case}?",
        "Which brand has more suitable {product_line} options for buyers in {geo}?",
        "Compare the value of {brand} and {competitor} phones across price ranges.",
        "What makes {brand} different from {competitor} in the {industry} market?",
        "Is a {brand} phone or a {competitor} phone more suitable for {use_case}?",
    ],

    # ── Transactional ─────────────────────────────────────────────────────────
    # User is ready to act. Purchase, trial, pricing research.
    IntentCategory.TRANSACTIONAL: [
        "What is the current price of {brand} {keyword} in {geo}?",
        "Where can I buy a {brand} smartphone in {geo}?",
        "Are there trade-in offers for {brand} phones in {geo}?",
        "How do I choose a {brand} phone for {use_case}?",
        "Where can I compare current {brand} phone models and prices?",
        "Does {brand} offer financing or installment plans for smartphones?",
        "What should I check before buying a {brand} phone online?",
        "Are refurbished {brand} phones available from authorized sellers?",
        "How can I find an authorized {brand} retailer near me in {geo}?",
        "Which {brand} phone should I consider for a budget of my choice?",
    ],

    # ── Problem-Aware ─────────────────────────────────────────────────────────
    # User has a pain point and is searching for a category of solution.
    # Brand may or may not be mentioned — high opportunity for brand insertion.
    IntentCategory.PROBLEM_AWARE: [
        "My phone battery drains quickly; what should I check before choosing a replacement?",
        "How can I take clearer photos in low light with a smartphone?",
        "What should I do if my phone gets slow during gaming or multitasking?",
        "I need a phone that lasts through a full day of video streaming; what should I compare?",
        "Which smartphone features can help with {use_case}?",
        "How do I choose a phone that works well for {use_case} without overspending?",
        "What should I consider if I am switching from an iPhone to an Android phone?",
        "How can I make a large smartphone easier to use one-handed?",
        "What should I look for in a durable phone for frequent travel?",
        "How do I compare phone repair and warranty options in {geo}?",
    ],

    # ── Feature-Aware ─────────────────────────────────────────────────────────
    # User knows the category, wants to verify a specific capability.
    IntentCategory.FEATURE_AWARE: [
        "Does {brand} offer a {product_line} with a camera suited to {use_case}?",
        "Which {brand} phones support a foldable display?",
        "Do {brand} smartphones support fast charging and wireless charging?",
        "What accessibility features are available on {brand} phones?",
        "Does {brand} offer a phone with enough storage for content creation?",
        "Which {brand} devices support AI-powered assistance?",
        "Can a {brand} phone handle gaming and multitasking well?",
        "What water and dust resistance do current {brand} phones offer?",
        "Do {brand} phones receive long-term software and security updates?",
        "Which {brand} phones work with Galaxy Watch and Galaxy Buds?",
    ],

    # ── Alternative ───────────────────────────────────────────────────────────
    # User is dissatisfied with current tool or wants to compare the whole market.
    IntentCategory.ALTERNATIVE: [
        "What are good alternatives to {competitor} phones for {use_case}?",
        "Which smartphone brands should I compare with {competitor} in {geo}?",
        "I want to switch from {competitor}; what should I consider from {brand}?",
        "What phones offer features similar to {competitor} for {use_case}?",
        "Which affordable alternatives to {competitor} are available in {geo}?",
        "What are the best Android alternatives for someone considering {competitor}?",
        "Which {industry} brands offer phones for mobile photography besides {competitor}?",
        "What should I compare before replacing my {competitor} phone?",
        "Is there a {brand} phone that could replace my {competitor} device?",
        "Which smartphone brands are worth considering for {audience} besides {competitor}?",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Template renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_template(
    template: str,
    brand:      str,
    competitors: list[str],
    keywords:    list[str],
    use_cases:   list[str],
    industry:    str,
    audience:    str,
    geography:   list[str],
    product_lines: list[str] | None = None,
    index:       int = 0,
) -> str:
    """
    Render a single template string with brand context values.

    Cycling: competitors, keywords, use_cases, and geography cycle through
    their lists using `index % len(list)` so consecutive renders use
    different values and produce more varied output.

    Args:
        template:    A template string with {placeholders}.
        brand:       Brand name.
        competitors: List of competitor names.
        keywords:    List of keywords.
        use_cases:   List of use cases.
        industry:    Industry string.
        audience:    Target audience string.
        geography:   List of geographies.
        index:       Position counter for cycling through lists.

    Returns:
        Rendered prompt string.
    """
    return template.format(
        brand      = brand,
        competitor = competitors[index % len(competitors)],
        keyword    = keywords[index % len(keywords)],
        use_case   = use_cases[index % len(use_cases)] if use_cases else "brand visibility tracking",
        product_line = product_lines[index % len(product_lines)] if product_lines else "smartphone",
        industry   = industry,
        audience   = audience,
        geo        = geography[index % len(geography)] if geography else "Global",
    )


def get_templates_for(category: IntentCategory) -> list[str]:
    """Return all template strings for a given intent category."""
    return TEMPLATES.get(category, [])


def total_template_count() -> int:
    """Total number of templates across all categories."""
    return sum(len(v) for v in TEMPLATES.values())
