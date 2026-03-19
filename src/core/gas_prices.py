"""
Fetch gas prices for Vancouver (gaswizard.ca) and Seattle metro (AAA).
Returns structured data for rendering in the email digest.
"""

import re
import urllib.request

VANCOUVER_URL = 'https://gaswizard.ca/gas-prices/vancouver/'
WASHINGTON_URL = 'https://gasprices.aaa.com/?state=WA'
_HEADERS = {'User-Agent': 'Mozilla/5.0'}


def fetch_all_gas_prices():
    """
    Fetch gas prices for both Vancouver and Seattle metro area.

    Returns:
        list of city dicts (may be empty but never None).
        Each dict: {city, date, fuels, source_url, unit, ...}
    """
    results = []
    van = _fetch_vancouver()
    if van:
        results.append(van)
    sea = _fetch_seattle()
    if sea:
        results.append(sea)
    return results


# ---------------------------------------------------------------------------
# Vancouver (gaswizard.ca)
# ---------------------------------------------------------------------------

def _fetch_vancouver():
    try:
        req = urllib.request.Request(VANCOUVER_URL, headers=_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"  ⚠️ Failed to fetch Vancouver gas prices: {e}")
        return None

    prices_match = re.search(
        r'<ul class="single-city-prices[^"]*">.*?<li>(.*?)</li>',
        html, re.DOTALL,
    )
    if not prices_match:
        print("  ⚠️ Could not find Vancouver gas price data")
        return None

    first_day = prices_match.group(1)

    date_match = re.search(
        r'<span class="daytext">(.*?)</span>\s*-\s*<span class="datetext">(.*?)</span>',
        first_day,
    )
    date_str = f"{date_match.group(1)} - {date_match.group(2)}" if date_match else ""

    fuel_types = re.findall(r'<div class="fueltitle">(.*?)</div>', first_day)
    fuel_prices = re.findall(
        r'<div class="fuelprice">([\d.]+)\s*\(<span class="price-direction (pd-up|pd-down)">(.*?)</span>\)',
        first_day,
    )

    fuels = []
    for i, ftype in enumerate(fuel_types):
        if i < len(fuel_prices):
            price, direction, change = fuel_prices[i]
            fuels.append({
                'type': ftype,
                'price': price,
                'change': change,
                'direction': 'up' if direction == 'pd-up' else 'down',
            })

    if not fuels:
        print("  ⚠️ Could not parse Vancouver fuel prices")
        return None

    avg_match = re.search(
        r'<span class="price">(\$[\d.]+)</span>\s*<span class="datetime">\(Reported at:\s*(.*?)\)</span>',
        html,
    )

    return {
        'city': 'Vancouver',
        'date': date_str,
        'fuels': fuels,
        'average_price': avg_match.group(1) if avg_match else None,
        'source_url': VANCOUVER_URL,
        'unit': '¢/L',
        'is_prediction': True,
    }


# ---------------------------------------------------------------------------
# Seattle metro area (AAA — Seattle-Bellevue-Everett)
# ---------------------------------------------------------------------------

def _fetch_seattle():
    try:
        req = urllib.request.Request(WASHINGTON_URL, headers=_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"  ⚠️ Failed to fetch Seattle gas prices: {e}")
        return None

    # Find the Seattle-Bellevue-Everett metro section
    seattle_idx = html.find('Seattle-Bellevue-Everett')
    if seattle_idx == -1:
        print("  ⚠️ Could not find Seattle section on AAA page")
        return None

    # Extract the first <tbody> after the Seattle heading
    table_match = re.search(
        r'<tbody>(.*?)</tbody>',
        html[seattle_idx:], re.DOTALL,
    )
    if not table_match:
        print("  ⚠️ Could not find Seattle gas price table")
        return None

    tbody = table_match.group(1)
    rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL)

    price_rows = {}
    for row in rows:
        cells = re.findall(r'<td>(.*?)</td>', row)
        if len(cells) >= 5:
            label = cells[0].strip()
            price_rows[label] = {
                'Regular': cells[1].strip(),
                'Mid': cells[2].strip(),
                'Premium': cells[3].strip(),
                'Diesel': cells[4].strip(),
            }

    current = price_rows.get('Current Avg.')
    yesterday = price_rows.get('Yesterday Avg.')
    if not current:
        print("  ⚠️ Could not parse Seattle gas prices")
        return None

    # Extract date from page header
    date_match = re.search(r'Price as of\s*(\d{1,2}/\d{1,2}/\d{2,4})', html)
    date_str = date_match.group(1) if date_match else ""

    fuels = []
    for ftype in ['Regular', 'Mid', 'Premium', 'Diesel']:
        cur = current.get(ftype, '')
        price_val = cur.lstrip('$')
        change = ''
        direction = ''
        if yesterday:
            yest = yesterday.get(ftype, '')
            try:
                diff = float(cur.lstrip('$')) - float(yest.lstrip('$'))
                if diff > 0:
                    change = f'+${diff:.3f}'
                    direction = 'up'
                elif diff < 0:
                    change = f'-${abs(diff):.3f}'
                    direction = 'down'
                else:
                    change = '$0.000'
                    direction = 'same'
            except ValueError:
                pass
        fuels.append({
            'type': ftype,
            'price': price_val,
            'change': change,
            'direction': direction,
        })

    return {
        'city': 'Seattle',
        'date': date_str,
        'fuels': fuels,
        'average_price': None,
        'source_url': WASHINGTON_URL,
        'unit': '$/gal',
    }
