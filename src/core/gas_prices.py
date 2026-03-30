"""
Fetch gas prices for Vancouver (gaswizard.ca) and Seattle metro (AAA).
Returns structured data for rendering in the email digest.
"""

import re
import urllib.request

VANCOUVER_URL = 'https://gaswizard.ca/gas-prices/vancouver/'
SEATTLE_EIA_URL = 'https://www.eia.gov/dnav/pet/pet_pri_gnd_dcus_Y48SE_w.htm'
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
        'unit': '¢/L',
        'is_prediction': True,
    }


# ---------------------------------------------------------------------------
# Seattle metro area (EIA — Weekly Retail Gasoline Prices)
# ---------------------------------------------------------------------------

def _fetch_seattle():
    try:
        req = urllib.request.Request(SEATTLE_EIA_URL, headers=_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"  ⚠️ Failed to fetch Seattle gas prices: {e}")
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
        print("  ⚠️ Could not parse Seattle gas prices")
        return None

    return {
        'city': 'Seattle',
        'date': date_str,
        'fuels': fuels,
        'average_price': None,
        'source_url': SEATTLE_EIA_URL,
        'unit': '$/gal',
    }
