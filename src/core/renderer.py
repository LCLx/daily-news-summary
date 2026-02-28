import html
from datetime import datetime
from pathlib import Path

_TEMPLATE = (Path(__file__).parent.parent / 'templates' / 'email.html').read_text(encoding='utf-8')

_H2_STYLE = 'color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:10px;margin-top:30px;'
_H3_STYLE = 'color:#34495e;margin-top:32px;margin-bottom:8px;padding-top:24px;border-top:1px solid #eee;'
_P_STYLE = 'margin:15px 0;'
_HR_STYLE = 'border:none;border-top:1px solid #eee;margin:25px 0;clear:both;'
_A_STYLE = 'color:#3498db;text-decoration:none;'
_ARTICLE_IMG_STYLE = (
    'display:block;max-width:100%;max-height:400px;width:auto;height:auto;'
    'object-fit:contain;border-radius:6px;margin:10px auto 16px;'
)
_DEALS_IMG_STYLE = (
    'width:110px;height:110px;max-width:110px;max-height:110px;'
    'object-fit:contain;float:left;margin:0 14px 6px 0;'
    'border-radius:4px;border:1px solid #eee;background:#f9f9f9;'
)
_DEALS_P_STYLE = 'margin:15px 0;white-space:pre-line;'


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
        is_deals = section.get('is_deals', False)

        parts.append(f'<h2 style="{_H2_STYLE}">{emoji} {html.escape(category)}</h2>')
        if is_deals:
            parts.append('<div>')

        for i, item in enumerate(section['items'], 1):
            parts.append(f'<h3 style="{_H3_STYLE}">{i}. {html.escape(item["title_zh"])}</h3>')

            if item.get('image_url'):
                img_style = _DEALS_IMG_STYLE if is_deals else _ARTICLE_IMG_STYLE
                parts.append(
                    f'<img onerror="this.remove()" style="{img_style}"'
                    f' src="{html.escape(item["image_url"])}" />'
                )

            if is_deals:
                price_parts = []
                if item.get('price'):
                    price_parts.append(f'<strong style="font-size:1.15em;">{html.escape(item["price"])}</strong>')
                if item.get('original_price') and item.get('discount'):
                    price_parts.append(
                        f'（原价 {html.escape(item["original_price"])}，'
                        f'省 {html.escape(item["discount"])}）'
                    )
                if item.get('store'):
                    price_parts.append(f'｜ 📍 {html.escape(item["store"])}')
                if price_parts:
                    parts.append(f'<p style="{_DEALS_P_STYLE}">{"".join(price_parts)}</p>')
                parts.append(f'<p style="{_DEALS_P_STYLE}">{html.escape(item["summary_zh"])}</p>')
                parts.append(f'<p style="{_DEALS_P_STYLE}">🔗 <a style="{_A_STYLE}" href="{html.escape(item["link"])}">查看优惠</a></p>')
            else:
                parts.append(f'<p style="{_P_STYLE}">{html.escape(item["summary_zh"])}</p>')
                parts.append(
                    f'<p style="{_P_STYLE}">🔗 原文: <a style="{_A_STYLE}" href="{html.escape(item["link"])}">'
                    f'{html.escape(item["title"])}</a><br/>'
                    f'📰 来源: {html.escape(item["source"])} | {html.escape(item["published"])}</p>'
                )
            parts.append(f'<hr style="{_HR_STYLE}"/>')

        if is_deals:
            parts.append('</div>')

    return '\n'.join(parts)
