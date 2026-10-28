"""AEOBrand: configurable, industry-neutral synthetic prompt templates.

These templates work across brand categories because they avoid assumptions
about smartphones or other specific product types. They remain template-based
examples; they are not evidence of real-world user queries or AI visibility.
"""

from models import IntentCategory

# All placeholders are supplied by render_template() below.
TEMPLATES: dict[IntentCategory, list[str]] = {
    IntentCategory.INFORMATIONAL: [
        "What should I consider when choosing a {product_line} for {use_case}?",
        "Which companies in {industry} offer solutions for {use_case}?",
        "What factors matter most when comparing {industry} products or services?",
        "How can I identify reliable options for {use_case}?",
        "What common mistakes should I avoid when choosing a {product_line}?",
        "How can I compare different {industry} providers objectively?",
        "Which {product_line} options are available in {geo}?",
        "What should {audience} consider before choosing a {product_line}?",
        "What are the typical advantages and disadvantages of {product_line} options?",
        "How can I evaluate whether a {product_line} meets my needs?",
    ],
    IntentCategory.COMPARATIVE: [
        "How does {brand} compare with {competitor} for {use_case}?",
        "What are the main differences between {brand} and {competitor}?",
        "Which is more suitable for {audience}, {brand} or {competitor}?",
        "How do {brand} and {competitor} compare in price and overall value?",
        "What strengths and weaknesses distinguish {brand} from {competitor}?",
        "How does customer support compare between {brand} and {competitor}?",
        "Which of {brand} and {competitor} better addresses {use_case}?",
        "What should I verify before choosing between {brand} and {competitor}?",
        "How do {brand} and {competitor} compare for buyers in {geo}?",
        "What factors should determine whether I choose {brand} over {competitor}?",
    ],
    IntentCategory.TRANSACTIONAL: [
        "Where can I find official information about {brand} products or services in {geo}?",
        "How can I check current pricing for {brand} offerings?",
        "What are the available ways to purchase or subscribe to {brand} offerings?",
        "Where can I compare the available {brand} {product_line} options?",
        "How do I contact {brand} to ask about {use_case}?",
        "What should I check before purchasing a {brand} {product_line}?",
        "Are there any current {brand} offers available in {geo}?",
        "Where can I find legitimate {brand} providers or sales channels?",
        "What options does {brand} provide for customers with different budgets?",
        "Where can I compare prices for {brand} {product_line} in {geo}?",
    ],
    IntentCategory.PROBLEM_AWARE: [
        "I'm struggling with {use_case}; what types of solutions should I compare?",
        "What should I do if existing options are not meeting my needs for {use_case}?",
        "I'm struggling with {use_case}; what should I look for in a {product_line}?",
        "Which features should I prioritize to improve {use_case}?",
        "How can I compare solutions for {use_case} without overspending?",
        "What are the common challenges people face with {use_case}?",
        "Which questions should I ask before selecting a solution for {use_case}?",
        "What are practical ways to improve outcomes for {use_case}?",
        "How do I know whether I need to replace my current solution for {use_case}?",
        "What should I look for if my current approach to {use_case} is not working?",
    ],
    IntentCategory.FEATURE_AWARE: [
        "Does {brand} offer features suited to {use_case}?",
        "Which {brand} {product_line} options support {use_case}?",
        "How do {brand} {product_line} options compare in features and price?",
        "How does {brand} support the needs of {audience}?",
        "What features should I look for in a {brand} {product_line}?",
        "Which {brand} features differentiate it from competing options?",
        "Can {brand} meet the requirements for {use_case}?",
        "What are the limitations of {brand} offerings for {use_case}?",
        "What support and maintenance options does {brand} provide?",
        "How can I verify whether {brand} offers the features I need?",
    ],
    IntentCategory.ALTERNATIVE: [
        "What are good alternatives to {competitor} for {use_case}?",
        "Which brands compete with {competitor} in {industry}?",
        "If I switch from {competitor}, what should I evaluate first?",
        "Which options provide similar benefits to {competitor} in {geo}?",
        "What alternatives to {competitor} suit {audience}?",
        "Which companies besides {competitor} support {use_case}?",
        "What are the trade-offs when replacing {competitor} with another provider?",
        "Are there affordable alternatives to {competitor} for {use_case}?",
        "Is {brand} a suitable alternative to {competitor} for {use_case}?",
        "Which {industry} brands are worth evaluating besides {competitor}?",
    ],
}


def render_template(
    template: str,
    brand: str,
    competitors: list[str],
    keywords: list[str],
    use_cases: list[str],
    industry: str,
    audience: str,
    geography: list[str],
    product_lines: list[str] | None = None,
    index: int = 0,
) -> str:
    """Fill a template with the configuration; cycle through list fields."""
    return template.format(
        brand=brand,
        competitor=competitors[index % len(competitors)] if competitors else "other providers",
        keyword=keywords[index % len(keywords)] if keywords else "relevant features",
        use_case=use_cases[index % len(use_cases)] if use_cases else "my needs",
        product_line=(
            product_lines[index % len(product_lines)]
            if product_lines else "product or service"
        ),
        industry=industry or "this industry",
        audience=audience or "buyers",
        geo=geography[index % len(geography)] if geography else "my region",
    )


def get_templates_for(category: IntentCategory) -> list[str]:
    return TEMPLATES.get(category, [])


def total_template_count() -> int:
    return sum(len(templates) for templates in TEMPLATES.values())
