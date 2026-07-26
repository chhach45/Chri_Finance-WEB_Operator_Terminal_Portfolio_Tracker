import os
import threading
import time
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from bs4 import BeautifulSoup

from helpers import apology, login_required, lookup, usd

# Configurazione Applicazione
app = Flask(__name__)
app.jinja_env.filters["usd"] = usd

# Configurazione Sessione
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Database SQLite
db = SQL("sqlite:///finance.db")

# Configurazione Telegram
TELEGRAM_TOKEN = "8784173703:AAFyJyAmGzu34wGwnwB2Fko2SaxMo66Wuko"
TELEGRAM_CHAT_ID = "6173375422"
ULTIME_NOTIZIE_BACKGROUND = {}


# LOGICA DI SUPPORTO & TELEGRAM
# ==========================================================

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.RequestException:
        pass

def fetch_news_html(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
    except requests.RequestException:
        pass
    return None

def parse_news(html_content, ticker):
    soup = BeautifulSoup(html_content, "html.parser")
    headlines = []
    ticker_lower = ticker.lower().strip()

    for tag in soup.find_all(["h3", "a"]):
        text = tag.get_text().strip()
        if len(text) > 25 and ticker_lower in text.lower():
            text_low = text.lower()
            if "terms" not in text_low and "privacy" not in text_low and "cookie" not in text_low and "reuters" not in text_low:
                if text not in headlines:
                    headlines.append(text)
        if len(headlines) >= 5:
            break
    return headlines

def monitoraggio_notizie_background():
    with app.app_context():
        while True:
            try:
                rows = db.execute("SELECT DISTINCT symbol FROM transactions")
                tickers = [row["symbol"] for row in rows]
                for ticker in tickers:
                    html = fetch_news_html(ticker)
                    if html:
                        notizie_correnti = parse_news(html, ticker)
                        notizie_precedenti = ULTIME_NOTIZIE_BACKGROUND.get(ticker, [])
                        for titolo in notizie_correnti:
                            if titolo not in notizie_precedenti:
                                testo_notifica = f"🔔 *New Alert for {ticker}* 🔔\n\n{titolo}"
                                send_telegram_message(testo_notifica)
                        ULTIME_NOTIZIE_BACKGROUND[ticker] = notizie_correnti
            except Exception:
                pass
            time.sleep(60)


# 🧠 CORE ENGINE: MOTORE DI CALCOLO UNIFICATO
# ==========================================================
def get_portfolio_state(user_id):
    """
    Calcola lo stato esatto del portafoglio applicando la regola:
    Available Cash = Total Portfolio Value - Holdings Value.
    La colonna 'cash' nel DB funge ora da unica sorgente di verità per il Total Portfolio Value.
    """
    # 1. Recupera il Total Portfolio Value fisso impostato dall'utente
    tpv = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    # 2. Recupera le posizioni aperte e calcola l'Holdings Value
    stocks = db.execute(
        "SELECT symbol, SUM(shares) as total_shares, AVG(price) as avg_price FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0",
        user_id
    )

    holdings_value = 0.0
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock["name"] = quote["name"]
            stock["current_price"] = quote["price"]
        else:
            stock["name"] = "N/A"
            stock["current_price"] = stock["avg_price"]

        stock["total"] = stock["total_shares"] * stock["current_price"]
        holdings_value += stock["total"]

    # 3. Calcola l'Available Cash come bilanciere dell'equazione
    available_cash = tpv - holdings_value

    return tpv, holdings_value, available_cash, stocks


# ROTTE FLASK (L'Interfaccia Web)
# ==========================================================

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    user_id = session["user_id"]

    # Modifica manuale del Total Portfolio Value
    if request.method == "POST":
        manual_total = request.form.get("manual_total")
        if manual_total:
            try:
                new_tpv = float(manual_total)
                # Aggiorniamo l'unica sorgente di verità nel DB
                db.execute("UPDATE users SET cash = ? WHERE id = ?", new_tpv, user_id)
                flash("Total Portfolio Value updated successfully!")
            except ValueError:
                return apology("Invalid numerical total", 400)
        return redirect("/")

    # Estrazione dello stato pulito
    tpv, holdings_value, available_cash, stocks = get_portfolio_state(user_id)

    return render_template("index.html", stocks=stocks, available_cash=available_cash, tpv=tpv)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol").upper().strip()
        shares = request.form.get("shares")
        price = request.form.get("price")

        if not symbol or not shares or not price:
            return apology("Invalid inputs", 400)

        try:
            shares = float(shares)
            price = float(price)
            if shares <= 0 or price <= 0:
                return apology("Quantity and price must be positive", 400)
        except ValueError:
            return apology("Invalid numerical inputs", 400)

        user_id = session["user_id"]

        # Generiamo lo stato per verificare i fondi
        tpv, holdings_value, available_cash, stocks = get_portfolio_state(user_id)

        cost = price * shares
        if available_cash < cost:
            return apology("Can't afford", 400)

        # INSERISCE SOLO LA TRANSAZIONE. NESSUN UPDATE SULLA CASSA!
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol, shares, price)

        flash(f"Successfully bought {shares} shares of {symbol} at ${price:.2f}! Available Cash recalculated.")
        return redirect("/")
    return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    if request.method == "POST":
        symbol = request.form.get("symbol").upper().strip()
        shares = request.form.get("shares")

        if not symbol or not shares:
            return apology("Invalid inputs", 400)

        try:
            shares = float(shares)
            if shares <= 0:
                return apology("Quantity must be positive", 400)
        except ValueError:
            return apology("Invalid numerical inputs", 400)

        row = db.execute(
            "SELECT SUM(shares) as total_shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol",
            user_id, symbol
        )

        if not row:
            return apology("Asset not owned", 400)

        total_posseduto = float(row[0]["total_shares"])
        if (total_posseduto - shares) < -0.01:
            return apology(f"Too many shares. Owned: {total_posseduto}", 400)

        quote = lookup(symbol)
        if not quote:
            return apology("Invalid ticker", 400)

        # INSERISCE SOLO LA TRANSAZIONE. NESSUN UPDATE SULLA CASSA!
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol, -shares, quote["price"])

        flash(f"Successfully sold {shares} shares of {symbol}! Available Cash recalculated.")
        return redirect("/")

    # Estraiamo i ticker in possesso per la dropdown della vendita
    stocks = db.execute(
        "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0",
        user_id
    )
    return render_template("sell.html", stocks=stocks)


@app.route("/news", methods=["GET", "POST"])
@login_required
def news():
    notizie = None
    ticker = None
    if request.method == "POST":
        ticker = request.form.get("symbol").upper().strip()
        html = fetch_news_html(ticker)
        if html:
            notizie = parse_news(html, ticker)
            if request.form.get("send_telegram") == "yes" and notizie:
                testo = f"🔔 *Latest News for {ticker}* 🔔\n\n" + "\n".join(notizie)
                send_telegram_message(testo)
                flash("News transmitted to Telegram!")
    return render_template("news.html", notizie=notizie, ticker=ticker)


@app.route("/taxes", methods=["GET", "POST"])
@login_required
def taxes():
    report = None
    if request.method == "POST":
        qty = float(request.form.get("quantity"))
        buy_price = float(request.form.get("buy_price"))
        sell_price = float(request.form.get("sell_price"))
        gain = (sell_price - buy_price) * qty
        tax = round(gain * 0.26, 2) if gain > 0 else 0.0
        report = {
            "gain": round(gain, 2),
            "tax": tax,
            "net": round(gain - tax if gain > 0 else gain, 2)
        }
    return render_template("taxes.html", report=report)


# ROTTE DI AUTENTICAZIONE
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password or password != request.form.get("confirmation"):
            return apology("Invalid registration details", 400)
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        except ValueError:
            return apology("Username taken", 400)
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid credentials", 403)
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# Inizializzazione Bot Telegram
send_telegram_message("The ChriFinance Web Bot is online!")
bg_thread = threading.Thread(target=monitoraggio_notizie_background, daemon=True)
bg_thread.start()
