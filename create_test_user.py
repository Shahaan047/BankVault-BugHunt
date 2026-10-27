
import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "bankvault.db"

username = "testuser2"
password = "TestUser2026!"
full_name = "Jordan Test"

connection = sqlite3.connect(DB_NAME)
connection.row_factory = sqlite3.Row

try:
    # Create the second fictional user if needed.
    user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if user is None:
        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash, full_name)
            VALUES (?, ?, ?)
            """,
            (username, generate_password_hash(password), full_name)
        )
        user_id = cursor.lastrowid
    else:
        user_id = user["id"]

    # Create a fictional account if needed.
    account = connection.execute(
        "SELECT id FROM accounts WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if account is None:
        cursor = connection.execute(
            """
            INSERT INTO accounts
                (user_id, account_number, account_type, balance)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, "BVTEST000002", "Savings", 5000.00)
        )
        account_id = cursor.lastrowid
    else:
        account_id = account["id"]

    # Create a test transaction if it doesn't already exist.
    transaction = connection.execute(
        """
        SELECT id FROM transactions
        WHERE user_id = ? AND reference = ?
        """,
        (user_id, "BUGHUNT-IDOR-002")
    ).fetchone()

    if transaction is None:
        cursor = connection.execute(
            """
            INSERT INTO transactions (
                user_id, account_id, name, reference,
                category, amount, type, status, transaction_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                account_id,
                "Test Deposit",
                "BUGHUNT-IDOR-002",
                "Test",
                500.00,
                "credit",
                "Completed",
                "2026-10-26"
            )
        )
        transaction_id = cursor.lastrowid
    else:
        transaction_id = transaction["id"]

    connection.commit()

    print("Test user and transaction are ready.")
    print("Username:", username)
    print("Password:", password)
    print("Transaction ID:", transaction_id)

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()
