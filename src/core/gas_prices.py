"""
Fetch gas prices for Vancouver (gaswizard.ca) and Seattle metro
(AAA primary, EIA fallback).
Returns structured data for rendering in the email digest.
"""

import re
import urllib.request

VANCOUVER_URL = 'https://gaswizard.ca/gas-prices/vancouver/'
AAA_WASHINGTON_URL = 'https://gasprices.aaa.com/?state=WA'
SEATTLE_EIA_URL = 'https://www.eia.gov/dnav/pet/pet_pri_gnd_dcus_Y48SE_w.htm'

_HEADERS = {'User-Agent': 'Mozilla/5.0'}
# AAA blocks generic UAs with 403; a full Chrome UA gets through.
_AAA_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
}


def fetch_all_gas_prices():
    """
    Fetch gas prices for both Vancouver and Seattle metro area.

    Returns:
        list of city dicts (may be empty but never None).
        Each dict: {city, date, fuels, source_url, source_name, unit, ...}
    """
    results = []
    van = _fetch_vancouver()
    if van:
        results.append(van)
    sea = _fetch_seattle_aaa() or _fetch_seattle_eia()
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
        r'<div class="fuelprice">([\d.]+)\s*\(<span class="price-direction (pd-up|pd-down|pd-nc)">(.*?)</span>\)',
        first_day,
    )

    fuels = []
    for i, ftype in enumerate(fuel_types):
        if i < len(fuel_prices):
            price, direction, change = fuel_prices[i]
            dir_map = {'pd-up': 'up', 'pd-down': 'down', 'pd-nc': 'same'}
            fuels.append({
                'type': ftype,
                'price': price,
                'change': change if change != 'n/c' else '0¢',
                'direction': dir_map.get(direction, 'same'),
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
        'source_name': 'Gas Wizard',
        'unit': '¢/L',
        'is_prediction': True,
    }


# ---------------------------------------------------------------------------
# Seattle metro area (AAA — Seattle-Bellevue-Everett, primary)
# ---------------------------------------------------------------------------

def _fetch_seattle_aaa():
    try:
        req = urllib.request.Request(AAA_WASHINGTON_URL, headers=_AAA_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"  ⚠️ Failed to fetch Seattle gas prices from AAA: {e}")
        return None

    seattle_idx = html.find('Seattle-Bellevue-Everett')
    if seattle_idx == -1:
        print("  ⚠️ Could not find Seattle section on AAA page")
        return None

    table_match = re.search(
        r'<tbody>(.*?)</tbody>',
        html[seattle_idx:], re.DOTALL,
    )
    if not table_match:
        print("  ⚠️ Could not find Seattle gas price table on AAA")
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
        print("  ⚠️ Could not parse Seattle gas prices from AAA")
        return None

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
        'source_url': AAA_WASHINGTON_URL,
        'source_name': 'AAA',
        'unit': '$/gal',
    }


# ---------------------------------------------------------------------------
# Seattle metro area (EIA Weekly Retail Gasoline Prices, fallback)
# ---------------------------------------------------------------------------

def _fetch_seattle_eia():
    try:
        req = urllib.request.Request(SEATTLE_EIA_URL, headers=_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"  ⚠️ Failed to fetch Seattle gas prices from EIA: {e}")
        return None

    # Extract the latest week date from column headers (last Series5 entry)
    dates = re.findall(r'<th class="Series5">([\d/]+)</th>', html)
    date_str = dates[-1] if dates else ""

    # Parse rows: find fuel type label then extract prices from that row
    # Each fuel type has two rows (all areas + conventional), we only need the first
    target_fuels = ['Regular', 'Midgrade', 'Premium']
    fuels = []

    for ftype in target_fuels:
        # Match the DataStub1 label, then capture the DataB and Current2 prices in the same row
        pattern = (
            r'DataStub1">' + re.escape(ftype) + r'</td>'
            r'.*?</table>\s*</td>'
            r'((?:\s*<td[^>]*class="DataB">[^<]*</td>)*)'
            r'\s*<td[^>]*class="Current2">([\d.]+)</td>'
        )
        m = re.search(pattern, html, re.DOTALL)
        if not m:
            continue

        current_price = m.group(2)
        # Get the last DataB value (previous week) for change calculation
        prev_prices = re.findall(r'class="DataB">([\d.]+)</td>', m.group(1))

        change = ''
        direction = ''
        if prev_prices:
            try:
                diff = float(current_price) - float(prev_prices[-1])
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
            'price': current_price,
            'change': change,
            'direction': direction,
        })

    if not fuels:
        print("  ⚠️ Could not parse Seattle gas prices from EIA")
        return None

    return {
        'city': 'Seattle',
        'date': date_str,
        'fuels': fuels,
        'average_price': None,
        'source_url': SEATTLE_EIA_URL,
        'source_name': 'EIA',
        'unit': '$/gal',
    }
