from core.config import CATEGORY_EMOJIS, CATEGORY_ZH_TO_RSS


def resolve_references(parsed_json, all_articles):
    """
    Resolve ref fields in Claude's JSON output to full article data.

    Refs are number-only (e.g. "3"), resolved against the section's category.

    Args:
        parsed_json: Parsed JSON dict from Claude (with "sections" key)
        all_articles: Original article dict keyed by RSS category name

    Returns:
        list of section dicts with full article data attached
    """
    sections = []
    for section in parsed_json.get('sections', []):
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
            # Support both number-only ("3") and legacy "Category:3" format
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
            # Deal-specific fields
            for field in ('price', 'original_price', 'discount', 'store'):
                if field in item:
                    resolved[field] = item[field]
            resolved_items.append(resolved)

        is_deals = rss_key == 'Deals'
        sections.append({'category': category, 'emoji': emoji, 'is_deals': is_deals, 'items': resolved_items})

    return sections
