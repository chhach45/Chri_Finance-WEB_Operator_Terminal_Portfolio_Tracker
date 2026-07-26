import csv
import sys
import os
import time
import threading
import requests
from bs4 import BeautifulSoup

# Telegram Bot configuration provided by the user.
TELEGRAM_TOKEN = "8784173703:AAFyJyAmGzu34wGwnwB2Fko2SaxMo66Wuko"
TELEGRAM_CHAT_ID = "6173375422"

#This memory is used ONLY by the background bot to prevent sending duplicate messages every minute.
ULTIME_NOTIZIE_BACKGROUND = {}


def main():
    # Initialize the portfolio CSV file with headers if it doesn't exist.
    if not os.path.exists("portfolio.csv"):
        with open("portfolio.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Ticker", "Quantity", "Buy Price"])

    # Send a confirmation test message when the software starts up.
    send_telegram_message("The bot is online!")

    # Start the background monitoring loop in a separate non-blocking daemon thread.
    background_thread = threading.Thread(target=monitoraggio_notizie_background, daemon=True)
    background_thread.start()

    # Main interactive CLI text menu loop
    while True:
        print("\n=== Personal Investment, News & Tax Tracker ===")
        print("1. View Portfolio & Total Value")
        print("2. Add Transaction")
        print("3. Remove Transaction/Ticker")
        print("4. Fetch Latest News (Yahoo Finance & Telegram)")
        print("5. Simulate Sale & Calculate Tax (26% Italian Capital Gain)")
        print("6. Exit")

        scelta = input("Choose an option: ").strip()

        if scelta == "1":
            mostra_portafoglio()
            attendi_ritorno_menu()
        elif scelta == "2":
            gestisci_aggiunta_transazione()
            attendi_ritorno_menu()
        elif scelta == "3":
            gestisci_rimozione_transazione()
            attendi_ritorno_menu()
        elif scelta == "4":
            gestisci_notizie()
        elif scelta == "5":
            gestisci_simulazione_tasse()
            attendi_ritorno_menu()
        elif scelta == "6":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Please try again.")


def monitoraggio_notizie_background():
    """Background task that checks Yahoo Finance for new headlines every 60 seconds dynamically."""
    time.sleep(5)

    while True:
        tickers = ottieni_tickers_da_portfolio()

        for ticker in tickers:
            html = fetch_news_html(ticker)
            if html:
                notizie_correnti = parse_news(html, ticker)
                notizie_precedenti = ULTIME_NOTIZIE_BACKGROUND.get(ticker, [])

                for titolo in notizie_correnti:
                    # If the title hasn't been seen in the last minute, send the message.
                    if titolo not in notizie_precedenti:
                        testo_notifica = f"🔔 *New Alert for {ticker}* 🔔\n\n{titolo}"
                        send_telegram_message(testo_notifica)

                # Updates the backend memory for the next cycle.
                ULTIME_NOTIZIE_BACKGROUND[ticker] = notizie_correnti

        time.sleep(60)


def ottieni_tickers_da_portfolio():
    """Helper function to extract a list of unique tickers from portfolio.csv."""
    tickers = set()
    if os.path.exists("portfolio.csv"):
        try:
            with open("portfolio.csv", "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Ticker"]:
                        tickers.add(row["Ticker"].upper())
        except Exception:
            pass
    return list(tickers)


def send_telegram_message(text):
    """Sends a text message to the configured Telegram chat using the HTTP Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def attendi_ritorno_menu():
    """Pauses the screen so the user can read results before clearing the menu."""
    print("\n" + "=" * 40)
    input("Press Enter to return to the main menu... ")


def mostra_portafoglio():
    """Reads the local CSV file and prints the total financial cost of the portfolio."""
    totale = 0.0
    print("\n--- Your Portfolio ---")
    try:
        with open("portfolio.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                print("Your portfolio is empty.")
                return
            for row in rows:
                ticker = row["Ticker"]
                qty = float(row["Quantity"])
                price = float(row["Buy Price"])
                valore = qty * price
                totale += valore
                print(f"Ticker: {ticker} | Qty: {qty} | Avg Buy Price: ${price:.2f} | Total: ${valore:.2f}")
            print("-" * 30)
            print(f"Total Portfolio Cost: ${totale:.2f}")
    except FileNotFoundError:
        print("Portfolio file not found.")


def gestisci_aggiunta_transazione():
    """Handles the user inputs to record a new transaction with float validation hints."""
    ticker = input("Ticker (e.g. AAPL): ").strip().upper()
    if not ticker:
        print("Error: Ticker cannot be empty.")
        return
    try:
        quantity = float(input("Quantity (use . for decimals, e.g. 10.50): "))
        price = float(input("Buy Price (use . for decimals, e.g. 142.25): "))
        add_transaction(ticker, quantity, price)
        print(f"\nSuccessfully added {quantity} shares of {ticker} at ${price:.2f}!")
    except ValueError as e:
        print(f"\nError: {e}. Please use numbers and use '.' for decimals.")


def gestisci_rimozione_transazione():
    """Handles the user inputs to remove all transactions for a specific ticker."""
    tickers_esistenti = ottieni_tickers_da_portfolio()
    if not tickers_esistenti:
        print("\nYour portfolio is already empty. Nothing to remove.")
        return

    print(f"\nCurrent tickers in your portfolio: {', '.join(tickers_esistenti)}")
    ticker = input("Enter the Ticker you want to remove fully: ").strip().upper()

    if ticker not in tickers_esistenti:
        print(f"Error: {ticker} is not in your portfolio.")
        return

    try:
        remove_ticker(ticker)
        print(f"\nSuccessfully removed all transactions for {ticker} from your portfolio.")
    except Exception as e:
        print(f"Error while removing ticker: {e}")


def gestisci_notizie():
    """Interactive loop to search for specific tickers news with an animated typing effect."""
    while True:
        ticker = input("\nEnter Ticker for news (e.g. AAPL) or press Enter to return to menu: ").strip().upper()

        if not ticker:
            break

        print(f"Fetching news for {ticker}...")
        html = fetch_news_html(ticker)
        if not html:
            print("Could not retrieve news at this moment.")
            continue

        #From now on, always fetch real-time news, without any limitations caused by previous searches.
        notizie = parse_news(html, ticker)
        if not notizie:
            print(f"No specific news headlines found for {ticker} right now.")
        else:
            print(f"\n--- 📺 Latest News Feed for {ticker} (Streaming...) ---")
            for i, titolo in enumerate(notizie, 1):
                print(f"{i}. ", end="", flush=True)
                for carattere in titolo:
                    sys.stdout.write(carattere)
                    sys.stdout.flush()
                    time.sleep(0.01)  #Smooth letter-by-letter scrolling.
                print()
                time.sleep(0.3)

            invia = input("\nDo you want to send these headlines to Telegram? (y/n): ").strip().lower()
            if invia == "y":
                testo_messaggio = f"🔔 *Latest News for {ticker}* 🔔\n\n"
                for i, titolo in enumerate(notizie, 1):
                    testo_messaggio += f"{i}. {titolo}\n"

                if send_telegram_message(testo_messaggio):
                    print("Sent successfully to Telegram!")
                else:
                    print("Failed to send message to Telegram.")

        print("\n" + "-" * 30)
        ancora = input("Would you like to search for another ticker? (y/n): ").strip().lower()
        if ancora != "y":
            break


def gestisci_simulazione_tasse():
    """Simulates a stock liquidation and calculates the potential Italian 26% tax."""
    try:
        qty = float(input("Quantity to sell (use . for decimals, e.g. 5.0): "))
        buy_price = float(input("Original buy price per share (use . for decimals, e.g. 100.00): "))
        sell_price = float(input("Hypothetical sell price per share (use . for decimals, e.g. 150.50): "))

        tax = calculate_capital_gain_tax(qty, buy_price, sell_price)
        gain = (sell_price - buy_price) * qty

        print("\n--- Tax Simulation Report ---")
        print(f"Gross Gain/Loss: ${gain:.2f}")
        print(f"Italian Tax Due (26% Capital Gain): ${tax:.2f}")
        if gain > 0:
            print(f"Net Profit: ${gain - tax:.2f}")
        else:
            print("No tax applied due to a financial loss.")
    except ValueError as e:
        print(f"\nError: {e}. Please ensure you enter valid positive numbers.")



# === REQUIRED CUSTOM FUNCTIONS FOR PYTEST (MUST BE DEF OUTSIDE MAIN LEVEL)


def add_transaction(ticker, quantity, price):
    """Validates the input variables and appends the asset transaction to the CSV."""
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    if price <= 0:
        raise ValueError("Price must be greater than zero")

    with open("portfolio.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ticker.upper(), quantity, price])


def remove_ticker(ticker):
    """Removes all rows matching the specified ticker from portfolio.csv."""
    if not ticker:
        raise ValueError("Ticker cannot be empty")

    rows_to_keep = []
    headers = ["Ticker", "Quantity", "Buy Price"]

    if os.path.exists("portfolio.csv"):
        with open("portfolio.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Ticker"].upper() != ticker.upper():
                    rows_to_keep.append(row)

        with open("portfolio.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows_to_keep:
                writer.writerow([row["Ticker"], row["Quantity"], row["Buy Price"]])


def fetch_news_html(ticker):
    """Downloads raw HTML source from Yahoo Finance ticker page using a real browser User-Agent."""
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
    except requests.RequestException:
        pass
    return None


def parse_news(html_content, ticker):
    """Parses Yahoo Finance HTML content to extract up to 5 strict relevant headlines text."""
    soup = BeautifulSoup(html_content, "html.parser")
    headlines = []

    ticker_lower = ticker.lower()

    for tag in soup.find_all(["h3", "a", "span"]):
        text = tag.get_text().strip()
        text_lower = text.lower()

        if len(text) > 25:
            if ticker_lower not in text_lower:
                if ticker_lower == "amzn" and "amazon" not in text_lower:
                    continue
                elif ticker_lower == "aapl" and "apple" not in text_lower:
                    continue
                elif ticker_lower == "tsla" and "tesla" not in text_lower:
                    continue
                elif ticker_lower == "goog" and "google" not in text_lower:
                    continue
                elif ticker_lower not in text_lower:
                    continue

            parole_da_evitare = ["Terms of Service", "Privacy Policy", "All quotes delayed", "Ad Feedback", "http"]
            if any(parola in text for parola in parole_da_evitare):
                continue

            if tag.name == "a":
                href = tag.get("href", "")
                if "/news/" not in href and "/mkt-proxy/" not in href:
                    continue

            if text not in headlines:
                headlines.append(text)

        if len(headlines) >= 5:
            break

    return headlines


def calculate_capital_gain_tax(quantity, buy_price, sell_price):
    """Calculates the 26% Italian Capital Gain substitute tax. Returns 0.0 if there's a loss."""
    if quantity <= 0 or buy_price <= 0 or sell_price <= 0:
         raise ValueError("Values must be positive numbers")

    guadagno_unitario = sell_price - buy_price
    guadagno_totale = guadagno_unitario * quantity

    if guadagno_totale > 0:
        return round(guadagno_totale * 0.26, 2)
    return 0.0


if __name__ == "__main__":
    main()
