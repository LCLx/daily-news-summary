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

# Gas price styles
_GAS_BOX_STYLE = (
    'background:linear-gradient(135deg,#f8f9fa,#e9ecef);border-radius:10px;'
    'padding:20px 24px;margin-bottom:16px;border:1px solid #dee2e6;'
)
_GAS_TITLE_STYLE = 'color:#2c3e50;margin:0 0 12px 0;font-size:1.05em;'
_GAS_TABLE_STYLE = 'width:100%;border-collapse:collapse;'
_GAS_TH_STYLE = 'text-align:left;padding:6px 12px;color:#6c757d;font-size:0.85em;border-bottom:1px solid #dee2e6;'
_GAS_TD_STYLE = 'padding:8px 12px;font-size:1em;'
_GAS_CHANGE_UP = 'color:#e74c3c;font-weight:bold;'
_GAS_CHANGE_DOWN = 'color:#27ae60;font-weight:bold;'


def build_email_html_from_json(sections, gas_prices=None):
    """
    Render resolved section data into a complete HTML email document.

    Args:
        sections: list of section dicts from digest.resolve_references()
        gas_prices: optional list of city dicts from gas_prices.fetch_all_gas_prices()

    Returns:
        str: Full HTML document string
    """
    date_str = datetime.now().strftime('%Y年%m月%d日')
    body_html = _render_body(sections)
    if gas_prices:
        body_html += _render_gas_section(gas_prices)
    return (
        _TEMPLATE
        .replace('$date_str', date_str)
        .replace('$body_html', body_html)
    )


def _render_gas_section(gas_prices_list):
    """Render gas prices for all cities as a section at the end."""
    parts = [
        f'<h2 style="{_H2_STYLE}">⛽ 油价速览</h2>',
    ]
    for gp in gas_prices_list:
        parts.append(_render_gas_city(gp))
    return '\n'.join(parts)


def _render_gas_city(gp):
    """Render gas prices for a single city as a compact info box."""
    unit = html.escape(gp.get('unit', ''))
    rows = []
    for fuel in gp['fuels']:
        change_html = ''
        if fuel.get('direction') and fuel.get('change'):
            if fuel['direction'] == 'up':
                change_html = f'<span style="{_GAS_CHANGE_UP}">▲ {html.escape(fuel["change"])}</span>'
            elif fuel['direction'] == 'down':
                change_html = f'<span style="{_GAS_CHANGE_DOWN}">▼ {html.escape(fuel["change"])}</span>'
            else:
                change_html = f'{html.escape(fuel["change"])}'
        rows.append(
            f'<tr>'
            f'<td style="{_GAS_TD_STYLE}">{html.escape(fuel["type"])}</td>'
            f'<td style="{_GAS_TD_STYLE}font-weight:bold;">{html.escape(fuel["price"])}</td>'
            f'<td style="{_GAS_TD_STYLE}">{change_html}</td>'
            f'</tr>'
        )

    avg = ''
    if gp.get('average_price'):
        avg = f'<p style="margin:10px 0 0;color:#6c757d;font-size:0.85em;">当前均价: {html.escape(gp["average_price"])}/L</p>'

    source_url = html.escape(gp['source_url'])
    source_name = 'Gas Wizard' if 'gaswizard' in gp['source_url'] else 'AAA'

    return (
        f'<div style="{_GAS_BOX_STYLE}">'
        f'<p style="{_GAS_TITLE_STYLE}">'
        f'📍 {html.escape(gp["city"])}'
        f' - {"Tomorrow\'s Prediction" if gp.get("is_prediction") else "Current"}'
        f'<span style="font-weight:normal;color:#6c757d;font-size:0.85em;"> ({unit})</span></p>'
        f'<table style="{_GAS_TABLE_STYLE}">'
        f'<tr><th style="{_GAS_TH_STYLE}">油品</th>'
        f'<th style="{_GAS_TH_STYLE}">价格</th>'
        f'<th style="{_GAS_TH_STYLE}">较昨日</th></tr>'
        + '\n'.join(rows) +
        f'</table>'
        f'{avg}'
        f'<p style="margin:8px 0 0;font-size:0.75em;color:#adb5bd;">'
        f'来源: <a style="{_A_STYLE}" href="{source_url}">{source_name}</a></p>'
        f'</div>\n'
    )


def _render_body(sections):
    parts = []
    for section in sections:
        category = section['category']
        emoji = section.get('emoji', '')

        parts.append(f'<h2 style="{_H2_STYLE}">{emoji} {html.escape(category)}</h2>')

        for i, item in enumerate(section['items'], 1):
            parts.append(f'<h3 style="{_H3_STYLE}">{i}. {html.escape(item["title_zh"])}</h3>')

            if item.get('image_url'):
                parts.append(
                    f'<img onerror="this.remove()" style="{_ARTICLE_IMG_STYLE}"'
                    f' src="{html.escape(item["image_url"])}" />'
                )

            parts.append(f'<p style="{_P_STYLE}">{html.escape(item["summary_zh"])}</p>')
            parts.append(
                f'<p style="{_P_STYLE}">🔗 原文: <a style="{_A_STYLE}" href="{html.escape(item["link"])}">'
                f'{html.escape(item["title"])}</a><br/>'
                f'📰 来源: {html.escape(item["source"])} | {html.escape(item["published"])}</p>'
            )
            parts.append(f'<hr style="{_HR_STYLE}"/>')

    return '\n'.join(parts)
