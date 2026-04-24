import json

from core import stock_market


def test_format_pct_adds_sign_from_direction():
    assert stock_market._format_pct('0.41%', 'up') == '+0.41%'
    assert stock_market._format_pct('0.41%', 'down') == '-0.41%'
    assert stock_market._format_pct('-0.41%', 'down') == '-0.41%'


def test_format_pct_handles_unchanged():
    assert stock_market._format_pct('', 'same') == '0.00%'
    assert stock_market._format_pct('UNCH', 'same') == '0.00%'


def test_format_bp_converts_percentage_points_to_basis_points():
    assert stock_market._format_bp('+0.035', 'up') == '+4bp'
    assert stock_market._format_bp('-0.025', 'down') == '−2bp'
    assert stock_market._format_bp('0.000', 'same') == '0bp'


def test_format_bp_preserves_unparseable_value():
    assert stock_market._format_bp('N/A', 'same') == 'N/A'


def test_format_snapshot_for_prompt():
    indices = [
        {'name': 'S&P 500', 'price': '5,000.00', 'change_display': '+0.50%'},
        {'name': '10Y Treasury Yield', 'price': '4.50%', 'change_display': '−2bp'},
    ]

    assert stock_market.format_snapshot_for_prompt(indices) == (
        'S&P 500: 5,000.00 (+0.50%)\n'
        '10Y Treasury Yield: 4.50% (−2bp)'
    )


def test_fetch_stock_indices_parses_cnbc_payload(monkeypatch):
    monkeypatch.setattr(stock_market, 'STOCK_INDICES', [
        {'symbol': '.SPX', 'name': 'S&P 500', 'unit': 'pct'},
        {'symbol': 'US10Y', 'name': '10Y Treasury Yield', 'unit': 'bp'},
    ])

    payload = {
        'FormattedQuoteResult': {
            'FormattedQuote': [
                {
                    'symbol': '.SPX',
                    'last': '5,000.00',
                    'changetype': 'UP',
                    'change': '25.00',
                    'change_pct': '0.50%',
                },
                {
                    'symbol': 'US10Y',
                    'last': '4.50%',
                    'changetype': 'DOWN',
                    'change': '-0.025',
                    'change_pct': '',
                },
            ],
        },
    }

    class FakeResponse:
        def read(self):
            return json.dumps(payload).encode('utf-8')

    monkeypatch.setattr(stock_market.urllib.request, 'urlopen', lambda req, timeout: FakeResponse())

    assert stock_market.fetch_stock_indices() == [
        {
            'symbol': '.SPX',
            'name': 'S&P 500',
            'price': '5,000.00',
            'direction': 'up',
            'change_display': '+0.50%',
        },
        {
            'symbol': 'US10Y',
            'name': '10Y Treasury Yield',
            'price': '4.50%',
            'direction': 'down',
            'change_display': '−2bp',
        },
    ]


def test_fetch_stock_indices_returns_empty_on_bad_payload(monkeypatch, capsys):
    class FakeResponse:
        def read(self):
            return b'{}'

    monkeypatch.setattr(stock_market.urllib.request, 'urlopen', lambda req, timeout: FakeResponse())

    assert stock_market.fetch_stock_indices() == []
    assert 'Unexpected CNBC response shape' in capsys.readouterr().out
