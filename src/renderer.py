import html
from datetime import datetime
from pathlib import Path

_TEMPLATE = (Path(__file__).parent / 'templates' / 'email.html').read_text(encoding='utf-8')

_ARTICLE_IMG_STYLE = (
    'display:block;max-width:100%;height:auto;'
    'margin:10px auto 16px;border-radius:6px;'
)
_DEALS_IMG_STYLE = (
    'width:110px !important;height:110px !important;'
    'max-width:110px !important;max-height:110px !important;'
    'object-fit:contain !important;float:left !important;'
    'margin:0 14px 6px 0 !important;border-radius:4px !important;'
    'border:1px solid #eee !important;background:#f9f9f9 !important;'
)


def build_email_html_from_json(sections):
    """
    Render resolved section data into a complete HTML email document.

    Args:
        sections: list of section dicts from digest.resolve_references()

    Returns:
        str: Full HTML document string
    """
    date_str = datetime.now().strftime('%Y年%m月%d日')
    body_html = _render_body(sections)
    return (
        _TEMPLATE
        .replace('$date_str', date_str)
        .replace('$body_html', body_html)
    )


def _render_body(sections):
    parts = []
    for section in sections:
        category = section['category']
        emoji = section.get('emoji', '')
        is_deals = category == '今日优惠'

        parts.append(f'<h2>{emoji} {html.escape(category)}</h2>')
        if is_deals:
            parts.append('<div class="deals-section">')

        for i, item in enumerate(section['items'], 1):
            parts.append(f'<h3>{i}. {html.escape(item["title_zh"])}</h3>')

            if item.get('image_url'):
                img_style = _DEALS_IMG_STYLE if is_deals else _ARTICLE_IMG_STYLE
                parts.append(
                    f'<img onerror="this.remove()" style="{img_style}"'
                    f' src="{html.escape(item["image_url"])}" />'
                )

            if is_deals:
                price_parts = []
                if item.get('price'):
                    price_parts.append(f'<strong>{html.escape(item["price"])}</strong>')
                if item.get('original_price') and item.get('discount'):
                    price_parts.append(
                        f'（原价 {html.escape(item["original_price"])}，'
                        f'省 {html.escape(item["discount"])}）'
                    )
                if item.get('store'):
                    price_parts.append(f'｜ 📍 {html.escape(item["store"])}')
                if price_parts:
                    parts.append(f'<p>{"".join(price_parts)}</p>')
                parts.append(f'<p>{html.escape(item["summary_zh"])}</p>')
                parts.append(f'<p>🔗 <a href="{html.escape(item["link"])}">查看优惠</a></p>')
            else:
                parts.append(f'<p>{html.escape(item["summary_zh"])}</p>')
                parts.append(
                    f'<p>🔗 原文: <a href="{html.escape(item["link"])}">'
                    f'{html.escape(item["title"])}</a><br/>'
                    f'📰 来源: {html.escape(item["source"])} | {html.escape(item["published"])}</p>'
                )
            parts.append('<hr/>')

        if is_deals:
            parts.append('</div>')

    return '\n'.join(parts)
