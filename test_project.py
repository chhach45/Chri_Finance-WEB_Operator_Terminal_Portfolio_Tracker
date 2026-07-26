import pytest
from project import add_transaction, calculate_capital_gain_tax, parse_news


def test_add_transaction_validation():
    with pytest.raises(ValueError):
        add_transaction("", 10, 150)
    with pytest.raises(ValueError):
        add_transaction("AAPL", -5, 150)
    with pytest.raises(ValueError):
        add_transaction("AAPL", 10, -10)


def test_calculate_capital_gain_tax():
    assert calculate_capital_gain_tax(10, 100.0, 150.0) == 130.0
    assert calculate_capital_gain_tax(10, 100.0, 80.0) == 0.0

    with pytest.raises(ValueError):
        calculate_capital_gain_tax(-5, 100, 150)


def test_parse_news_with_mock_html():
    # A simple linear dummy HTML containing 'aapl' in both the link and the text.
    mock_html = """
    <html>
        <body>
            <a href="/news/aapl-stock-update-123">aapl stock is rising today because of high sales</a>
            <a href="/news/market-update">market update for Nvidia investors today</a>
        </body>
    </html>
    """
    notizie = parse_news(mock_html, "AAPL")

    # It should only find the news article containing 'aapl'
    assert len(notizie) == 1
    assert notizie[0] == "aapl stock is rising today because of high sales"
