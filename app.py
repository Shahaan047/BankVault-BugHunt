from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
from datetime import datetime, date
from collections import defaultdict
import json
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-to-a-random-secret-key"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

# =====================================
# DATABASE CONFIGURATION
# =====================================

DATABASE = "bankvault.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection
    # =====================================
# DASHBOARD ANALYTICS
# =====================================

def get_dashboard_analytics(connection, user_id):

    current_month = date.today().replace(day=1)

    # Retrieve this user's transactions from the last 12 months.
    rows = connection.execute(
        """
        SELECT
            amount,
            type,
            category,
            transaction_date
        FROM transactions
        WHERE user_id = ?
          AND transaction_date >= ?
          AND transaction_date <= ?
        ORDER BY transaction_date ASC, id ASC
        """,
        (
            user_id,
            (date.today().replace(day=1) -
             __import__("datetime").timedelta(days=365)).isoformat(),
            date.today().isoformat()
        )
    ).fetchall()

    # Prepare monthly income and expense totals.
    monthly_income = defaultdict(float)
    monthly_expenses = defaultdict(float)

    # Prepare spending by category for the current month.
    category_spending = defaultdict(float)

    total_income = 0.0
    total_expenses = 0.0

    for row in rows:

        amount = float(row["amount"])
        transaction_type = row["type"]
        category = row["category"]
        transaction_date = date.fromisoformat(
            row["transaction_date"]
        )

        month_key = transaction_date.strftime("%Y-%m")

        if transaction_type == "credit":

            monthly_income[month_key] += amount

            if transaction_date.year == date.today().year and \
               transaction_date.month == date.today().month:

                total_income += amount

        elif transaction_type == "debit":

            monthly_expenses[month_key] += amount

            if transaction_date.year == date.today().year and \
               transaction_date.month == date.today().month:

                total_expenses += amount

                category_spending[category] += amount

    # Create labels for the most recent 12 calendar months.
    chart_labels = []
    income_data = []
    expense_data = []

    for offset in range(11, -1, -1):

        month_number = current_month.month - offset
        year = current_month.year

        while month_number <= 0:
            month_number += 12
            year -= 1

        month_start = date(year, month_number, 1)
        month_key = month_start.strftime("%Y-%m")

        chart_labels.append(month_start.strftime("%b"))
        income_data.append(round(monthly_income[month_key], 2))
        expense_data.append(round(monthly_expenses[month_key], 2))

    # Sort spending categories from largest to smallest.
    spending_categories = sorted(
        [
            {
                "name": category,
                "amount": round(amount, 2)
            }
            for category, amount in category_spending.items()
        ],
        key=lambda item: item["amount"],
        reverse=True
    )

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "chart_labels": chart_labels,
        "income_data": income_data,
        "expense_data": expense_data,
        "spending_categories": spending_categories
    }


# =====================================
# INITIALIZE DATABASE
# =====================================

# =====================================
# INITIALIZE DATABASE
# =====================================

def init_db():

    connection = get_db_connection()

    # Create users table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL
        )
    """)

    # Create accounts table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_number TEXT UNIQUE NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create transactions table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            name TEXT NOT NULL,
            reference TEXT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('credit', 'debit')),
            status TEXT NOT NULL DEFAULT 'Completed',
            transaction_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # Create notifications table
    connection.execute("""
    
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            related_transaction_id INTEGER,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (related_transaction_id) REFERENCES transactions(id)
        )
    """)
        # Create cards table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            cardholder_name TEXT NOT NULL,
            masked_number TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active'
                CHECK(status IN ('Active', 'Frozen')),
            spending_limit REAL NOT NULL DEFAULT 25000,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()

    # Create demo user if necessary
    existing_user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("demo",)
    ).fetchone()

    if existing_user is None:

        password_hash = generate_password_hash("DemoPass123!")

        connection.execute(
            """
            INSERT INTO users (username, password_hash, full_name)
            VALUES (?, ?, ?)
            """,
            ("demo", password_hash, "Alex Morgan")
        )

        connection.commit()

    # Get demo user ID
    demo_user = connection.execute(
        "SELECT id, full_name FROM users WHERE username = ?",
        ("demo",)
    ).fetchone()

    demo_user_id = demo_user["id"]

    # Create a demo card if one doesn't already exist
    existing_card = connection.execute(
        "SELECT id FROM cards WHERE user_id = ? LIMIT 1",
        (demo_user_id,)
    ).fetchone()

    if existing_card is None:
        connection.execute(
            """
            INSERT INTO cards (
                user_id, cardholder_name, masked_number,
                expiry_date, status, spending_limit
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                demo_user_id,
                demo_user["full_name"] if "full_name" in demo_user.keys() else "Alex Morgan",
                "•••• •••• •••• 4821",
                "10/29",
                "Active",
                25000.00
            )
        )
        connection.commit()

    # Create sample accounts only if they don't exist
    existing_accounts = connection.execute(
        "SELECT COUNT(*) AS total FROM accounts WHERE user_id = ?",
        (demo_user_id,)
    ).fetchone()["total"]

    if existing_accounts == 0:

        connection.execute(
            """
            INSERT INTO accounts
                (user_id, account_number, account_type, balance)
            VALUES (?, ?, ?, ?)
            """,
            (demo_user_id, "BV100004821", "Savings", 165000.00)
        )

        connection.execute(
            """
            INSERT INTO accounts
                (user_id, account_number, account_type, balance)
            VALUES (?, ?, ?, ?)
            """,
            (demo_user_id, "BV100007193", "Current", 83500.00)
        )

        connection.commit()

    # Get the demo user's accounts
    demo_accounts = connection.execute(
        """
        SELECT id, account_type
        FROM accounts
        WHERE user_id = ?
        """,
        (demo_user_id,)
    ).fetchall()

    # Create sample transactions only if they don't exist
    existing_transactions = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE user_id = ?
        """,
        (demo_user_id,)
    ).fetchone()["total"]

    if existing_transactions == 0:

        account_ids = {
            account["account_type"]: account["id"]
            for account in demo_accounts
        }

        sample_transactions = [

            (
                demo_user_id,
                account_ids["Savings"],
                "Monthly Salary",
                "Salary credit",
                "Income",
                75000.00,
                "credit",
                "Completed",
                "2026-10-18"
            ),

            (
                demo_user_id,
                account_ids["Savings"],
                "Online Shopping",
                "Shopping payment",
                "Shopping",
                2499.00,
                "debit",
                "Completed",
                "2026-10-17"
            ),

            (
                demo_user_id,
                account_ids["Current"],
                "Electricity Bill",
                "Monthly utility bill",
                "Utilities",
                1850.00,
                "debit",
                "Completed",
                "2026-10-16"
            ),

            (
                demo_user_id,
                account_ids["Savings"],
                "Received Transfer",
                "Money received",
                "Transfer",
                5000.00,
                "credit",
                "Completed",
                "2026-10-15"
            ),

            (
                demo_user_id,
                account_ids["Current"],
                "Restaurant Payment",
                "Dining payment",
                "Food & Dining",
                950.00,
                "debit",
                "Completed",
                "2026-10-14"
            )

        ]

        connection.executemany(
            """
            INSERT INTO transactions (
                user_id,
                account_id,
                name,
                reference,
                category,
                amount,
                type,
                status,
                transaction_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sample_transactions
        )

        connection.commit()

    connection.close()
# =====================================
# LOGIN REQUIRED
# =====================================

def login_required(view_function):

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:
            flash("Please log in to access your dashboard.", "error")

            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/about")
def about():
    return render_template("about.html")


# =====================================
# DASHBOARD
# =====================================

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db_connection()

    user_id = session["user_id"]
    # Get the latest name from the database
    user_row = connection.execute(
    "SELECT full_name FROM users WHERE id = ?",
    (user_id,)
    ).fetchone()

    full_name = user_row["full_name"] if user_row else "Customer"
    session["full_name"] = full_name

    # Retrieve the logged-in user's accounts
    accounts = connection.execute(
        """
        SELECT id, account_number, account_type, balance
        FROM accounts
        WHERE user_id = ?
        ORDER BY id
        """,
        (user_id,)
    ).fetchall()

    # Calculate total balance from stored account balances
    total_balance = sum(
        account["balance"]
        for account in accounts
    )

    # Prepare account information for the template
    savings_balance = 0
    current_balance = 0
    savings_last4 = "----"
    current_last4 = "----"

    for account_item in accounts:

        if account_item["account_type"] == "Savings":

            savings_balance = account_item["balance"]

            savings_last4 = account_item["account_number"][-4:]

        elif account_item["account_type"] == "Current":

            current_balance = account_item["balance"]

            current_last4 = account_item["account_number"][-4:]

    account = {
        "name": full_name,
        "total_balance": total_balance,
        "savings_balance": savings_balance,
        "current_balance": current_balance,
        "savings_last4": savings_last4,
        "current_last4": current_last4
    }

        # Retrieve the logged-in user's transactions
    transaction_rows = connection.execute(
        """
        SELECT
            name,
            reference,
            category,
            amount,
            type,
            status,
            transaction_date
        FROM transactions
        WHERE user_id = ?
        ORDER BY transaction_date DESC, id DESC
        LIMIT 20
        """,
        (user_id,)
    ).fetchall()

    # Format transaction dates
    transactions = []

    for row in transaction_rows:
        transaction = dict(row)

        transaction["transaction_date"] = datetime.strptime(
            transaction["transaction_date"],
            "%Y-%m-%d"
        ).strftime("%d %b %Y")

        transactions.append(transaction)

    # Calculate dashboard analytics
    analytics = get_dashboard_analytics(connection, user_id)
    # Count unread notifications for the logged-in user
    unread_count = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE user_id = ? AND is_read = 0
        """,
        (user_id,)
    ).fetchone()["total"]

    # Close database connection
    connection.close()

    # Display dashboard
    return render_template(
        "dashboard.html",
        account=account,
        transactions=transactions,
        analytics=analytics,
        unread_count=unread_count
    )


# =====================================
# LOGIN
# =====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Redirect already logged-in users.
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:

            flash("Please enter both username and password.", "error")

            return render_template("login.html")

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT id, username, password_hash, full_name
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")
# =====================================
# MY ACCOUNTS
# =====================================

@app.route("/accounts")
@login_required
def accounts():

    connection = get_db_connection()

    user_id = session["user_id"]

    # Retrieve accounts belonging to the logged-in user.
    account_rows = connection.execute(
        """
        SELECT
            id,
            account_number,
            account_type,
            balance
        FROM accounts
        WHERE user_id = ?
        ORDER BY id
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    # Prepare account information for the template.
    accounts_list = []

    for row in account_rows:

        account_item = dict(row)

        # Mask the account number.
        account_item["masked_number"] = (
            "•••• " + account_item["account_number"][-4:]
        )

        account_item["status"] = "Active"

        accounts_list.append(account_item)

    total_balance = sum(
        account["balance"]
        for account in accounts_list
    )

    return render_template(
        "accounts.html",
        accounts=accounts_list,
        total_balance=total_balance,
        full_name=session.get("full_name", "Customer")
    )
    # =====================================
# TRANSACTION HISTORY
# =====================================

@app.route("/transactions")
@login_required
def transaction_history():

    connection = get_db_connection()

    user_id = session["user_id"]

    # Retrieve transactions belonging to the logged-in user.
    transaction_rows = connection.execute(
        """
        SELECT
            id,
            account_id,
            name,
            reference,
            category,
            amount,
            type,
            status,
            transaction_date
        FROM transactions
        WHERE user_id = ?
        ORDER BY transaction_date DESC, id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    transactions_list = []

    for row in transaction_rows:

        transaction = dict(row)

        transaction["formatted_date"] = (
            datetime.strptime(
                transaction["transaction_date"],
                "%Y-%m-%d"
            ).strftime("%d %b %Y")
        )

        transactions_list.append(transaction)

    total_income = sum(
        transaction["amount"]
        for transaction in transactions_list
        if transaction["type"] == "credit"
    )

    total_expenses = sum(
        transaction["amount"]
        for transaction in transactions_list
        if transaction["type"] == "debit"
    )

    successful_transactions = sum(
        1
        for transaction in transactions_list
        if transaction["status"].lower() in ["completed", "success", "successful"]
    )

    return render_template(
        "transactions.html",
        transactions=transactions_list,
        total_transactions=len(transactions_list),
        total_income=total_income,
        total_expenses=total_expenses,
        successful_transactions=successful_transactions
    )

@app.route("/notifications")
@login_required
def notifications():
    connection = get_db_connection()

    user_id = session["user_id"]

    notification_list = connection.execute(
        """
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    ).fetchall()

    unread_count = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE user_id = ? AND is_read = 0
        """,
        (user_id,)
    ).fetchone()["total"]

    connection.close()

    return render_template(
        "notifications.html",
        notifications=notification_list,
        unread_count=unread_count
    )
@app.route("/notifications/read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    user_id = session["user_id"]
    connection = get_db_connection()

    try:
        connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ? AND user_id = ?
            """,
            (notification_id, user_id)
        )

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("notifications"))


@app.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    user_id = session["user_id"]
    connection = get_db_connection()

    try:
        connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = ? AND is_read = 0
            """,
            (user_id,)
        )

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("notifications"))

# =====================================
# BANK STATEMENTS
# =====================================

@app.route("/statements")
@login_required
def statements():

    connection = get_db_connection()

    user_id = session["user_id"]

    # Get the user's accounts.
    accounts = connection.execute(
        """
        SELECT id, account_number, account_type, balance
        FROM accounts
        WHERE user_id = ?
        ORDER BY id
        """,
        (user_id,)
    ).fetchall()

    # Read filter values from the URL.
    selected_account = request.args.get("account_id", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Validate account ownership before using the account.
    account = None

    if selected_account:
        account = connection.execute(
            """
            SELECT id, account_number, account_type, balance
            FROM accounts
            WHERE id = ? AND user_id = ?
            """,
            (selected_account, user_id)
        ).fetchone()

    # Default to the first account if none was selected.
    if account is None and accounts:
        account = accounts[0]

    transactions = []

    total_credits = 0
    total_debits = 0

    if account:

        query = """
            SELECT
                id,
                name,
                reference,
                category,
                amount,
                type,
                status,
                transaction_date
            FROM transactions
            WHERE user_id = ?
              AND account_id = ?
        """

        parameters = [user_id, account["id"]]

        # Apply the optional date filters.
        if start_date:
            query += " AND transaction_date >= ?"
            parameters.append(start_date)

        if end_date:
            query += " AND transaction_date <= ?"
            parameters.append(end_date)

        query += " ORDER BY transaction_date DESC, id DESC"

        transactions = connection.execute(
            query,
            parameters
        ).fetchall()

        total_credits = sum(
            row["amount"]
            for row in transactions
            if row["type"] == "credit"
        )

        total_debits = sum(
            row["amount"]
            for row in transactions
            if row["type"] == "debit"
        )

    connection.close()

    # The account balance is the current demo balance.
    closing_balance = account["balance"] if account else 0

    # This is a provisional opening-balance calculation.
    # We'll refine it when we implement reliable balance tracking.
    opening_balance = closing_balance - total_credits + total_debits

    return render_template(
        "statements.html",
        accounts=accounts,
        account=account,
        transactions=transactions,
        selected_account=str(account["id"]) if account else "",
        start_date=start_date,
        end_date=end_date,
        total_credits=total_credits,
        total_debits=total_debits,
        opening_balance=opening_balance,
        closing_balance=closing_balance
    )
# =====================================
# TRANSACTION DETAILS
# =====================================

@app.route("/transaction/<int:transaction_id>")
@login_required
def transaction_details(transaction_id):

    user_id = session["user_id"]

    connection = get_db_connection()

    try:
        # Retrieve the transaction and its account details.
        transaction = connection.execute(
            """
            SELECT
                transactions.id,
                transactions.account_id,
                transactions.name,
                transactions.reference,
                transactions.category,
                transactions.amount,
                transactions.type,
                transactions.status,
                transactions.transaction_date,
                accounts.account_type,
                accounts.account_number
            FROM transactions
            LEFT JOIN accounts
                ON transactions.account_id = accounts.id
            WHERE transactions.id = ? 
            """, #IDOR B1
            (transaction_id,)
        ).fetchone()

        # Only allow users to view their own transactions.
        if transaction is None:
            flash("Transaction not found.", "error")
            return redirect(url_for("transaction_history"))

        transaction = dict(transaction)

        # Format the transaction date.
        transaction["formatted_date"] = datetime.strptime(
            transaction["transaction_date"],
            "%Y-%m-%d"
        ).strftime("%d %B %Y")

        return render_template(
            "transaction_details.html",
            transaction=transaction
        )

    finally:
        connection.close()
        
# =====================================
# MONEY TRANSFER
# =====================================

@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer_money():

    user_id = session["user_id"]
    connection = get_db_connection()

    try:
        if request.method == "POST":

            source_id = request.form.get("source_account", "").strip()
            recipient_number = request.form.get(
                "recipient_account", ""
            ).strip()
            amount_text = request.form.get("amount", "").strip()
            description = request.form.get("description", "").strip()

            # Validate required fields.
            if not source_id or not recipient_number or not amount_text:
                flash("Please complete all required fields.", "error")
                return redirect(url_for("transfer_money"))

            # Validate amount.
            try:
                amount = round(float(amount_text), 2)
            except (ValueError, TypeError):
                flash("Enter a valid transfer amount.", "error")
                return redirect(url_for("transfer_money"))

            if amount <= 0:
                flash("Transfer amount must be greater than zero.", "error")
                return redirect(url_for("transfer_money"))

            # Reject excessive precision such as 10.999.
            try:
                if float(amount_text) != amount:
                    flash("Amount cannot have more than two decimal places.", "error")
                    return redirect(url_for("transfer_money"))
            except ValueError:
                flash("Enter a valid transfer amount.", "error")
                return redirect(url_for("transfer_money"))

            # Retrieve the source account owned by the logged-in user.
            source = connection.execute(
                """
                SELECT id, account_number, account_type, balance
                FROM accounts
                WHERE id = ? AND user_id = ?
                """,
                (source_id, user_id)
            ).fetchone()

            if source is None:
                flash("Invalid source account.", "error")
                return redirect(url_for("transfer_money"))

            # Retrieve the recipient account.
            # For this first version, it must belong to the same user.
            recipient = connection.execute(
                """
                SELECT id, account_number, account_type, balance
                FROM accounts
                WHERE account_number = ? AND user_id = ?
                """,
                (recipient_number, user_id)
            ).fetchone()

            if recipient is None:
                flash(
                    "Recipient account not found. "
                    "Use one of your own BankVault accounts.",
                    "error"
                )
                return redirect(url_for("transfer_money"))

            if source["id"] == recipient["id"]:
                flash(
                    "Choose a different account as the recipient.",
                    "error"
                )
                return redirect(url_for("transfer_money"))

            if source["balance"] < amount:
                flash("Insufficient balance for this transfer.", "error")
                return redirect(url_for("transfer_money"))

            # Show confirmation before processing the transfer.
            if request.form.get("confirm_transfer") != "yes":
                return render_template(
                    "transfer_confirm.html",
                    source=source,
                    recipient=recipient,
                    amount=amount,
                    description=description or "Account Transfer"
                )

            # Begin an atomic database transaction.
            connection.execute("BEGIN IMMEDIATE")

            # Recheck the source balance inside the transaction.
            current_source = connection.execute(
                """
                SELECT balance
                FROM accounts
                WHERE id = ? AND user_id = ?
                """,
                (source["id"], user_id)
            ).fetchone()

            if current_source is None or current_source["balance"] < amount:
                connection.rollback()
                flash("Insufficient balance for this transfer.", "error")
                return redirect(url_for("transfer_money"))

            # Deduct money from the source account.
            connection.execute(
    """
    UPDATE accounts
    SET balance = balance - ?
    WHERE id = ? AND user_id = ?
    """,
    (amount, source["id"], user_id)
)

             # Add money to the recipient account.
            connection.execute(
    """
    UPDATE accounts
    SET balance = balance + ?
    WHERE id = ? AND user_id = ?
    """,
    (amount, recipient["id"], user_id)
)

            # Create a reference for this transfer.
            reference = "BV" + datetime.now().strftime("%Y%m%d%H%M%S%f")

            transaction_date = date.today().isoformat()

            transfer_description = description or "Account Transfer"

            # Record the debit.
            connection.execute(
                """
                INSERT INTO transactions (
                    user_id, account_id, name, reference,
                    category, amount, type, status, transaction_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    source["id"],
                    "Transfer to " + recipient["account_number"][-4:],
                    reference,
                    "Transfer",
                    amount,
                    "debit",
                    "Completed",
                    transaction_date
                )
            )

            # Record the credit.
            connection.execute(
                """
                INSERT INTO transactions (
                    user_id, account_id, name, reference,
                    category, amount, type, status, transaction_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    recipient["id"],
                    "Transfer from " + source["account_number"][-4:],
                    reference,
                    "Transfer",
                    amount,
                    "credit",
                    "Completed",
                    transaction_date
                )
            )

            connection.commit()
            connection.commit()

            # Create notification for the sender.
            connection.execute(
                """
                INSERT INTO notifications (
                    user_id, title, message, category
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    "Money Sent",
                    f"Your transfer of ₹{amount:,.2f} to account "
                    f"ending in {recipient['account_number'][-4:]} "
                    f"was completed successfully. Reference: {reference}",
                    "transfer"
                )
            )

            # Create notification for the recipient.
            connection.execute(
                """
                INSERT INTO notifications (
                    user_id, title, message, category
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    "Money Received",
                    f"₹{amount:,.2f} was credited to your account "
                    f"ending in {recipient['account_number'][-4:]}. "
                    f"Reference: {reference}",
                    "transfer"
                )
            )

            # Save both notifications.
            connection.commit()

            flash(
                f"Transfer of ₹{amount:,.2f} completed successfully. "
                f"Reference: {reference}",
                "success"
            )

            return redirect(url_for("transfer_money"))

        # GET request: show the user's accounts.
        accounts = connection.execute(
            """
            SELECT id, account_number, account_type, balance
            FROM accounts
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,)
        ).fetchall()

        return render_template(
            "transfer.html",
            accounts=accounts
        )

    except Exception:
        connection.rollback()
        app.logger.exception("Money transfer failed.")
        flash(
            "The transfer could not be completed. "
            "Please try again.",
            "error"
        )
        return redirect(url_for("transfer_money"))

    finally:
        connection.close()

# =====================================
# PROFILE & SETTINGS
# =====================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    user_id = session["user_id"]

    connection = get_db_connection()

    try:
        if request.method == "POST":

            full_name = request.form.get("full_name", "").strip()

            if not full_name:
                flash("Full name cannot be empty.", "error")

            elif len(full_name) > 100:
                flash("Full name cannot exceed 100 characters.", "error")

            else:
                connection.execute(
                    """
                    UPDATE users
                    SET full_name = ?
                    WHERE id = ?
                    """,
                    (full_name, user_id)
                )

                connection.commit()

                session["full_name"] = full_name

                flash("Your profile has been updated successfully.", "success")

                return redirect(url_for("profile"))

        user = connection.execute(
            """
            SELECT id, username, full_name
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if user is None:
            session.clear()
            flash("Please log in again.", "error")
            return redirect(url_for("login"))

        return render_template("profile.html", user=user)

    finally:
        connection.close()

# =====================================
# CHANGE PASSWORD
# =====================================

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    user_id = session["user_id"]

    if request.method == "POST":

        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password or not confirm_password:
            flash("Please complete all password fields.", "error")
            return redirect(url_for("change_password"))

        if len(new_password) < 8:
            flash("Your new password must contain at least 8 characters.", "error")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("The new passwords do not match.", "error")
            return redirect(url_for("change_password"))

        connection = get_db_connection()

        try:
            user = connection.execute(
                """
                SELECT password_hash
                FROM users
                WHERE id = ?
                """,
                (user_id,)
            ).fetchone()

            if user is None or not check_password_hash(
                user["password_hash"],
                current_password
            ):
                flash("Your current password is incorrect.", "error")
                return redirect(url_for("change_password"))

            new_password_hash = generate_password_hash(new_password)

            connection.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
                """,
                (new_password_hash, user_id)
            )

            connection.commit()

            # Create a security notification
            connection.execute(
                """
                INSERT INTO notifications (
                    user_id, title, message, category
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    "Security Alert: Password Changed",
                    "Your BankVault password was changed successfully. "
                    "If it wasn't you, please secure "
                    "your account immediately.",
                    "security"
                )
            )

            connection.commit()

            flash("Your password has been changed successfully.", "success")
            return redirect(url_for("profile"))

        finally:
            connection.close()

    return render_template("change_password.html")

# =====================================
# LOGOUT
# =====================================

@app.route("/logout", methods=["GET", "POST"])
# UNSAFE LOGOUT B3 
def logout():

    session.clear()

    flash("You have been logged out successfully.", "success")

    return redirect(url_for("login"))


# =====================================
# BUG HUNT CHALLENGE: SQL INJECTION
# INTENTIONALLY VULNERABLE — LAB COPY ONLY
# =====================================
@app.route("/challenge/search")
@login_required
def challenge_search():
    term = request.args.get("q", "")
    connection = get_db_connection()
    try:
        # Intentional SQL injection flaw for the isolated TechFest challenge.
        query = f"""
            SELECT id, user_id, name, category, amount, type, status
            FROM transactions
            WHERE user_id = {session["user_id"]}
              AND name LIKE '%{term}%'
            ORDER BY id DESC
            LIMIT 100
        """
        rows = connection.execute(query).fetchall()
        return render_template("challenge_search.html", rows=rows, term=term)
    finally:
        connection.close()


# =====================================
# BUG HUNT CHALLENGE: SENSITIVE INFORMATION EXPOSURE
# INTENTIONALLY EXPOSES FICTIONAL DEMO DATA — LAB COPY ONLY
# =====================================
@app.route("/challenge/diagnostics")
def challenge_diagnostics():
    connection = get_db_connection()
    try:
        rows = connection.execute("""
            SELECT users.username, users.full_name,
                   accounts.account_number, accounts.account_type,
                   accounts.balance
            FROM users
            JOIN accounts ON accounts.user_id = users.id
            ORDER BY users.id, accounts.id
        """).fetchall()
        return render_template("challenge_diagnostics.html", rows=rows)
    finally:
        connection.close()


# =====================================
# RUN APPLICATION
# =====================================
# =====================================
# BANK CARDS
# =====================================


@app.route("/cards")
@login_required
def cards():
    connection = get_db_connection()

    try:
        user_id = session["user_id"]

        card = connection.execute(
            """
            SELECT
                cards.id,
                users.full_name AS cardholder_name,
                cards.masked_number,
                cards.expiry_date,
                cards.status,
                cards.spending_limit
            FROM cards
            JOIN users ON cards.user_id = users.id
            WHERE cards.user_id = ?
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

        return render_template("cards.html", card=card)

    finally:
        connection.close()


        
# =====================================
# PAY BILLS
# =====================================

@app.route("/pay-bills", methods=["GET", "POST"])
@login_required
def pay_bills():
    connection = get_db_connection()
    user_id = session["user_id"]

    try:
        if request.method == "POST":
            bill_type = request.form.get("bill_type", "").strip()
            consumer_number = request.form.get(
                "consumer_number", ""
            ).strip()
            account_id = request.form.get("account_id", "").strip()
            amount_text = request.form.get("amount", "").strip()

            # Validate bill type.
            allowed_bill_types = {
                "Electricity",
                "Water",
                "Internet",
                "Mobile Recharge"
            }

            if bill_type not in allowed_bill_types:
                flash("Please select a valid bill type.", "error")
                return redirect(url_for("pay_bills"))

            # Validate consumer number.
            if (
                not consumer_number
                or len(consumer_number) > 50
                or not consumer_number.isprintable()
            ):
                flash("Please enter a valid consumer or account number.", "error")
                return redirect(url_for("pay_bills"))

            # Validate amount.
            try:
                amount = round(float(amount_text), 2)
            except (ValueError, TypeError):
                flash("Please enter a valid payment amount.", "error")
                return redirect(url_for("pay_bills"))

            if amount <= 0 or amount > 1000000:
                flash("Enter an amount between ₹1 and ₹10,00,000.", "error")
                return redirect(url_for("pay_bills"))

            # Reject amounts with more than two decimal places.
            try:
                if float(amount_text) != amount:
                    flash("Amount cannot have more than two decimal places.", "error")
                    return redirect(url_for("pay_bills"))
            except ValueError:
                flash("Please enter a valid payment amount.", "error")
                return redirect(url_for("pay_bills"))

            # Verify that the selected account belongs to this user.
            account = connection.execute(
                """
                SELECT id, account_number, account_type, balance
                FROM accounts
                WHERE id = ? AND user_id = ?
                """,
                (account_id, user_id)
            ).fetchone()

            if account is None:
                flash("Please select a valid account.", "error")
                return redirect(url_for("pay_bills"))

            # Check available balance.
            if account["balance"] < amount:
                flash("Insufficient balance to pay this bill.", "error")
                return redirect(url_for("pay_bills"))

            # Record the payment and deduct the balance atomically.
            try:
                connection.execute("BEGIN IMMEDIATE")

                current_account = connection.execute(
                    """
                    SELECT balance
                    FROM accounts
                    WHERE id = ? AND user_id = ?
                    """,
                    (account_id, user_id)
                ).fetchone()

                if (
                    current_account is None
                    or current_account["balance"] < amount
                ):
                    connection.rollback()
                    flash("Insufficient balance to pay this bill.", "error")
                    return redirect(url_for("pay_bills"))

                connection.execute(
                    """
                    UPDATE accounts
                    SET balance = balance - ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (amount, account_id, user_id)
                )

                reference = "BV" + datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )

                connection.execute(
                    """
                    INSERT INTO transactions (
                        user_id,
                        account_id,
                        name,
                        reference,
                        category,
                        amount,
                        type,
                        status,
                        transaction_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        account["id"],
                        bill_type + " Bill Payment",
                        reference,
                        bill_type,
                        amount,
                        "debit",
                        "Completed",
                        date.today().isoformat()
                    )
                )

                connection.execute(
                    """
                    INSERT INTO notifications (
                        user_id, title, message, category
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        "Bill Payment Successful",
                        f"Your {bill_type.lower()} payment of "
                        f"₹{amount:,.2f} was completed successfully. "
                        f"Reference: {reference}",
                        "payment"
                    )
                )

                connection.commit()

            except Exception:
                connection.rollback()
                app.logger.exception("Bill payment failed.")
                flash(
                    "The payment could not be completed. Please try again.",
                    "error"
                )
                return redirect(url_for("pay_bills"))

            flash(
                f"{bill_type} payment of ₹{amount:,.2f} completed successfully.",
                "success"
            )
            return redirect(url_for("pay_bills"))

        # GET request: retrieve this user's accounts.
        accounts = connection.execute(
            """
            SELECT id, account_number, account_type, balance
            FROM accounts
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,)
        ).fetchall()

        return render_template(
            "pay_bills.html",
            accounts=accounts
        )

    finally:
        connection.close()

if __name__ == "__main__":
    init_db()
    app.run(debug=True)