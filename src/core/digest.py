from core.config import CATEGORY_EMOJIS


def resolve_references(parsed_json, all_articles):
    """
    Resolve ref fields in Claude's JSON output to full article data.

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
        resolved_items = []

        for item in section.get('items', []):
            ref = item.get('ref', '')
            if ':' not in ref:
                print(f"⚠️ Invalid ref format: {ref}")
                continue
            cat_key, idx_str = ref.rsplit(':', 1)
            try:
                idx = int(idx_str)
            except ValueError:
                print(f"⚠️ Invalid ref index: {ref}")
                continue
            cat_articles = all_articles.get(cat_key, [])
            if idx < 1 or idx > len(cat_articles):
                print(f"⚠️ Ref out of range: {ref} (have {len(cat_articles)} articles)")
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

        sections.append({'category': category, 'emoji': emoji, 'items': resolved_items})

    return sections
