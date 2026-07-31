# Chri Finance Manager Web version - WEB Operator Terminal & Portfolio Tracker

#### Video Demo: https://youtu.be/TX_H2Wz6_Dg
#### Description:

**ChriFinance** is a highly responsive, dynamic web application built using **Python (Flask)** and an **SQLite** database, designed to manage, calculate, and track user investment portfolios. Moving away from traditional corporate dashboards, ChriFinance opts for an immersive, high-contrast, military-inspired **Cyberpunk Operator Terminal** user interface.

The primary problem this application solves is database-to-frontend synchronization lag and portfolio discrepancies commonly found in financial log systems. By shifting away from standard paradigms where cash and asset tracking are mutated independently, ChriFinance enforces a rigid, closed-loop system governed by an explicit mathematical invariant:

$$\text{Available Cash} = \text{Total Portfolio Value} - \text{Holdings Value}$$

In this architectural design, the user directly controls their **Total Portfolio Value** as the single source of truth inside the system, while the **Available Cash** automatically flows and recalibrates around real-time transactions and asset volumes.

---

## File Structure and Component Architecture

Below is a breakdown of every file written for this project and its respective structural responsibility:

### 1. Backend Core Architecture (`app.py`)
This is the master file hosting the main Python backend application layer. It handles server configuration, cryptographic session state generation, SQL database interaction, and automation routing.
- **Centralized Engine**: Contains the crucial helper function `get_portfolio_state(user_id)`. This function is the mathematical anchor of the program; it queries the SQLite database for the user's asset volume, aggregates average load prices, calls financial lookup APIs, and isolates the equation to output the current financial matrix. By routing the root `/` page, the `/buy` portal, and the `/sell` portal through this single engine, data divergence is entirely prevented.
- **Asynchronous Scraping Background Thread**: Spawns an automated `threading.Thread` routine upon initialization. This thread continuously cycles every 60 seconds to execute automated web scraping via BeautifulSoup on Yahoo Finance URLs for assets currently held in the database. When new articles are found, they are dispatched asynchronously using the Telegram Bot API to notify the operator without introducing any execution overhead or freezing the frontend rendering.

### 2. Frontend View Templates (`templates/`)
- **`layout.html`**: The UI skeleton defining the global structure of the application. It includes the structural header elements, navigation menu items, flashes, and the CSS grid layouts that shape the dark-mode theme.
- **`index.html`**: The core control deck dashboard. Displays high-contrast metrics for Available Cash and Total Portfolio Value side-by-side. It renders a clean grid loop mapping out held assets, open positions, average load prices, and total valuations. It features an integrated POST form enabling operators to immediately scale their Total Portfolio Value.
- **`buy.html`**: Contains the input pipeline fields for ticker tracking, asset accumulation, and personal load price entry.
- **`sell.html`**: The asset liquidation form. Engineered with a specialized aesthetic override, it adopts a bold red color palette to represent alert states during asset offloading. The ticker drop-down selection menu dynamically populates based on active positions held in the database.
- **`news.html` & `taxes.html`**: Analytical view fields enabling live ticker news reporting and a capital gains tax calculator simulating a 26% national tax rate deduction.

### 3. Data Storage (`finance.db`)
An SQLite database consisting of:
- **`users` Table**: Retains cryptographic hashes of user passwords, system indexing keys, and maps the primary record variable (`cash`) serving as the master indicator for the total portfolio value.
- **`transactions` Table**: An immutable ledger capturing every market trade. Asset liquidations are logged with standard negative mathematical signs, permitting instant volume calculations through clean SQL aggregations (`SUM(shares)`).

---

## Design Decisions and Rationales

During the development lifecycle, two critical design choices were evaluated:

### 1. Invariant Portfolio vs. Volatile Cassa
Traditionally, stock tracking software locks your money (`cash`) and lets the total value change dynamically based on stock values. For this operator terminal, we flipped the logic entirely: **Total Portfolio Value is the Anchor**.
This is because users tracking external private funds or manually testing risk strategies often want to see how much cash they *should* have left if they commit a fixed cap to the market. By treating `Available Cash` as a dynamic delta variable instead of a static database record, we eliminated bugs where database writing delays could lead to double-spending or false balances during rapid buying and selling.

### 2. Asynchronous Threaded Notifications
Integrating Telegram alerts into the main web request cycle would have drastically degraded user experience, as `requests.post` timeouts can stall page rendering. To avoid this, a daemon background thread was implemented. It monitors the database independently, handling API handshakes in parallel while keeping the Flask web router fast and lightweight.

---

## How to Execute and Submit

1. Navigate to the project folder inside your terminal:
   ```bash
   cd /workspaces/193009774/project

2. Launch the Flask system server:

Bash
flask --app app.py run --debug



