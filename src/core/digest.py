from core.config import CATEGORY_EMOJIS, CATEGORY_ZH_TO_RSS


def resolve_references(parsed_json, all_articles):
    """
    Resolve ref fields in the LLM JSON 'sections' output to full article data.

    Refs are number-only (e.g. "3"), resolved against the section's category.

    Args:
        parsed_json: Parsed JSON dict from the LLM backend (with "sections" key)
        all_articles: Original article dict keyed by RSS category name

    Returns:
        list of section dicts with full article data attached
    """
    sections = []
    for section in parsed_json.get('sections', []):
        if not isinstance(section, dict):
            print(f"⚠️ Skipping malformed section (expected dict, got {type(section).__name__}): {section!r:.80}")
            continue
        category = section.get('category', '')
        emoji = CATEGORY_EMOJIS.get(category, '')
        rss_key = CATEGORY_ZH_TO_RSS.get(category, '')

        if not rss_key:
            print(f"⚠️ Unknown category: {category}")
            continue

        cat_articles = all_articles.get(rss_key, [])
        resolved_items = []

        for item in section.get('items', []):
            ref = item.get('ref', '')
            idx_str = ref.rsplit(':', 1)[-1] if ':' in ref else ref
            try:
                idx = int(idx_str)
            except ValueError:
                print(f"⚠️ Invalid ref: {ref} in {category}")
                continue
            if idx < 1 or idx > len(cat_articles):
                print(f"⚠️ Ref {ref} out of range in {category} (have {len(cat_articles)} articles)")
                continue

            original = cat_articles[idx - 1]
            resolved = {
                'title_zh': item.get('title_zh', ''),
                'summary_zh': item.get('summary_zh', ''),
                'link': original.get('link', ''),
                'title': original.get('title', ''),
                'source': original.get('source', ''),
                'published': original.get('published', ''),
                'image_url': original.get('image_url'),
            }
            resolved_items.append(resolved)

        sections.append({'category': category, 'emoji': emoji, 'items': resolved_items})

    return sections


def resolve_market_pulse(parsed_json, stock_articles):
    """
    Resolve market_pulse refs to full article data for the 'related reading' strip.

    Args:
        parsed_json: Parsed JSON dict from the LLM backend (may contain "market_pulse" key)
        stock_articles: Stock-market articles fed to Claude as market_pulse input

    Returns:
        dict with keys {summary, drivers, watch, related}, or None if absent
    """
    pulse = parsed_json.get('market_pulse') if isinstance(parsed_json, dict) else None
    if not pulse or not isinstance(pulse, dict):
        return None

    related = []
    for ref in pulse.get('refs', []):
        try:
            idx = int(str(ref).rsplit(':', 1)[-1])
        except ValueError:
            print(f"⚠️ Invalid market_pulse ref: {ref}")
            continue
        if idx < 1 or idx > len(stock_articles):
            print(f"⚠️ market_pulse ref {ref} out of range (have {len(stock_articles)} stock articles)")
            continue
        original = stock_articles[idx - 1]
        related.append({
            'title': original.get('title', ''),
            'link': original.get('link', ''),
            'source': original.get('source', ''),
        })

    return {
        'summary': pulse.get('summary', ''),
        'drivers': [d for d in pulse.get('drivers', []) if isinstance(d, dict)],
        'watch': [w for w in pulse.get('watch', []) if isinstance(w, str)],
        'related': related,
    }
