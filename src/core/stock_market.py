"""
Fetch US stock index snapshots from CNBC's public quote API.
Returns structured data for rendering in the market_pulse section.
"""

import json
import urllib.parse
import urllib.request

from core.config import STOCK_INDICES

_CNBC_URL = (
    'https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol'
    '?symbols={symbols}&requestMethod=quick&noform=1&partnerId=2&fund=1'
    '&exthrs=1&output=json'
)
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}


def fetch_stock_indices():
    """
    Fetch one quote per configured index in a single CNBC API call.

    Returns:
        list of dicts (may be empty):
          {symbol, name, price, direction, change_display}
        `direction` ∈ {'up', 'down', 'same'}; `change_display` is the
        pre-formatted string ('-0.41%' or '+3bp') for rendering.
    """
    symbols = '|'.join(idx['symbol'] for idx in STOCK_INDICES)
    url = _CNBC_URL.format(symbols=urllib.parse.quote(symbols, safe='|.'))
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        payload = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  ⚠️ Failed to fetch stock indices: {e}")
        return []

    try:
        quotes = payload['FormattedQuoteResult']['FormattedQuote']
    except (KeyError, TypeError):
        print(f"  ⚠️ Unexpected CNBC response shape")
        return []

    by_symbol = {q.get('symbol'): q for q in quotes}

    results = []
    for idx in STOCK_INDICES:
        q = by_symbol.get(idx['symbol'])
        if not q:
            print(f"  ⚠️ Missing quote for {idx['symbol']}")
            continue

        last = q.get('last', '')
        changetype = q.get('changetype', '').upper()
        change_raw = q.get('change', '')
        change_pct = q.get('change_pct', '')

        direction = 'up' if changetype == 'UP' else 'down' if changetype == 'DOWN' else 'same'

        if idx['unit'] == 'bp':
            change_display = _format_bp(change_raw, direction)
        else:
            change_display = _format_pct(change_pct, direction)

        results.append({
            'symbol': idx['symbol'],
            'name': idx['name'],
            'price': last,
            'direction': direction,
            'change_display': change_display,
        })
    return results


def _format_pct(change_pct_raw, direction):
    """Indices: CNBC already formats as e.g. '-0.41%'; normalize 'UNCH'."""
    if not change_pct_raw or change_pct_raw == 'UNCH':
        return '0.00%'
    s = change_pct_raw.strip()
    if direction != 'same' and not s.startswith(('+', '-', '−')):
        s = ('+' if direction == 'up' else '-') + s
    return s


def _format_bp(change_raw, direction):
    """Yield change in percentage points → basis points display."""
    if not change_raw or change_raw == 'UNCH':
        return '0bp'
    try:
        pp = float(change_raw.replace('+', '').replace('−', '-'))
    except ValueError:
        return change_raw
    bp = round(pp * 100)
    if bp == 0:
        return '0bp'
    sign = '+' if bp > 0 else '−'
    return f'{sign}{abs(bp)}bp'


def format_snapshot_for_prompt(indices):
    """Compact one-line-per-index format for the summary prompt."""
    if not indices:
        return ''
    return '\n'.join(f"{i['name']}: {i['price']} ({i['change_display']})" for i in indices)
