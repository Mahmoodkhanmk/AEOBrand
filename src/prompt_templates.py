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
        "What are the best {keyword} tools available for {industry} companies?",
        "How does {keyword} work and why does it matter for modern marketing?",
        "What is {keyword} and how is it different from traditional SEO?",
        "Can you explain {keyword} to a {audience} with no technical background?",
        "What are the top-rated platforms for {keyword} in {geo}?",
        "How do large enterprises measure {keyword} across multiple AI models?",
        "What metrics are used to evaluate {keyword} performance?",
        "Which {industry} companies are leading the space in {keyword}?",
        "What should I know before investing in a {keyword} solution?",
        "How has {keyword} evolved over the past two years?",
    ],

    # ── Comparative ───────────────────────────────────────────────────────────
    # User is evaluating options. Most valuable intent — brand is directly named.
    IntentCategory.COMPARATIVE: [
        "How does {brand} compare to {competitor} for {use_case}?",
        "{brand} vs {competitor}: which platform is better for {industry}?",
        "What are the main differences between {brand} and {competitor}?",
        "Which tool is more accurate for {keyword} — {brand} or {competitor}?",
        "Compare {brand} and {competitor} in terms of pricing, features, and support.",
        "For a {audience}, would {brand} or {competitor} be the better choice?",
        "How do {brand} and {competitor} handle {use_case} differently?",
        "Which platform offers better {keyword} reporting — {brand} or {competitor}?",
        "What makes {brand} stand out from {competitor} in the {industry} market?",
        "Is {brand} more reliable than {competitor} for enterprise {use_case}?",
    ],

    # ── Transactional ─────────────────────────────────────────────────────────
    # User is ready to act. Purchase, trial, pricing research.
    IntentCategory.TRANSACTIONAL: [
        "How much does {brand} cost for a {industry} company with 500 employees?",
        "Does {brand} offer a free trial or demo for enterprise customers?",
        "What is the pricing model for {brand} — per seat, per usage, or flat fee?",
        "How do I get started with {brand} for {use_case}?",
        "Where can I book a demo of {brand} for my {audience}?",
        "Does {brand} offer custom pricing for large-scale {industry} deployments?",
        "What implementation support does {brand} provide during onboarding?",
        "How quickly can {brand} be integrated into an existing {industry} tech stack?",
        "What is the ROI of investing in {brand} for {use_case}?",
        "Are there any discounts or annual plans available for {brand}?",
    ],

    # ── Problem-Aware ─────────────────────────────────────────────────────────
    # User has a pain point and is searching for a category of solution.
    # Brand may or may not be mentioned — high opportunity for brand insertion.
    IntentCategory.PROBLEM_AWARE: [
        "My brand doesn't appear in ChatGPT answers — how do I fix that?",
        "How can I find out if AI assistants are mentioning my competitors more than my brand?",
        "I have no visibility into how LLMs represent my company — what tool can help?",
        "How do I measure my brand's presence in AI-generated content at scale?",
        "We're losing market share in AI search — what strategies actually work for {keyword}?",
        "How do I track whether {competitor} is outperforming us in AI-generated recommendations?",
        "What should {industry} companies do when their brand visibility in AI drops?",
        "I can't tell if our content strategy is improving our {keyword} — how do I measure it?",
        "How do I diagnose why my {industry} brand is invisible to LLMs?",
        "What is the fastest way to improve brand mentions in AI assistant responses?",
    ],

    # ── Feature-Aware ─────────────────────────────────────────────────────────
    # User knows the category, wants to verify a specific capability.
    IntentCategory.FEATURE_AWARE: [
        "Does {brand} support tracking brand mentions across multiple AI models simultaneously?",
        "Can {brand} monitor {keyword} in real time or only on a scheduled basis?",
        "Does {brand} provide sentiment analysis on AI-generated brand mentions?",
        "Can {brand} track competitor mentions alongside brand mentions in the same report?",
        "Does {brand} have an API for integrating {keyword} data into our BI tools?",
        "Can {brand} export reports to PDF, CSV, or connect to Tableau?",
        "Does {brand} support {keyword} tracking across non-English language models?",
        "Is {brand} able to identify which specific prompts trigger brand mentions?",
        "Does {brand} offer white-label reporting for {audience}?",
        "Can {brand} generate automated alerts when brand sentiment changes significantly?",
    ],

    # ── Alternative ───────────────────────────────────────────────────────────
    # User is dissatisfied with current tool or wants to compare the whole market.
    IntentCategory.ALTERNATIVE: [
        "What are the best alternatives to {competitor} for {use_case}?",
        "Which {keyword} tools are better than {competitor} for {industry}?",
        "I'm looking for a {competitor} replacement — what do you recommend for {use_case}?",
        "What {keyword} platforms are available besides {competitor} and {brand}?",
        "Are there any open-source alternatives to {competitor} for {keyword}?",
        "What is the most affordable alternative to {competitor} for small {industry} teams?",
        "Which {keyword} tool would you recommend instead of {competitor} for {geo} companies?",
        "What are the top 5 {keyword} platforms if I'm not using {competitor}?",
        "Which {industry} tools compete directly with {competitor} in the {keyword} space?",
        "Is there a better option than {competitor} for a {audience} focused on {use_case}?",
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
