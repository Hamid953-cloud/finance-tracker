import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from database import get_connection

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def hash_answer(answer):
    return hashlib.sha256(answer.lower().strip().encode()).hexdigest()

def check_password_strength(password):
    """Password strength check karo"""
    errors = []
    if len(password) < 8:
        errors.append("At least 8 characters required")
    if not any(c.isupper() for c in password):
        errors.append("At least 1 uppercase letter required")
    if not any(c.islower() for c in password):
        errors.append("At least 1 lowercase letter required")
    if not any(c.isdigit() for c in password):
        errors.append("At least 1 number required")
    return errors

def is_valid_username(username):
    return (username.isalnum() and
            len(username) >= 3 and
            username[0].isalpha())

def register_user(username, password, secret_question, secret_answer):
    """Naya user register karo"""
    conn = get_connection()
    c = conn.cursor()

    # Check username exists
    c.execute("SELECT username FROM users WHERE username = ?",
              (username,))
    if c.fetchone():
        conn.close()
        return False, "username_taken"

    # Save user
    c.execute("""
        INSERT INTO users
        (username, password_hash, secret_question, secret_answer)
        VALUES (?, ?, ?, ?)
    """, (username, hash_password(password),
          secret_question, hash_answer(secret_answer)))

    # Default settings
    c.execute("""
        INSERT OR IGNORE INTO settings (username, currency_symbol)
        VALUES (?, ?)
    """, (username, "Rs."))

    conn.commit()
    conn.close()
    return True, "success"

def login_user(username, password):
    """User login karo — failed attempts track karo"""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()

    if not user:
        conn.close()
        return False, "user_not_found"

    # Lock check karo
    if user["locked_until"]:
        locked_until = datetime.fromisoformat(user["locked_until"])
        if datetime.now() < locked_until:
            remaining = int(
                (locked_until - datetime.now()).total_seconds() / 60)
            conn.close()
            return False, f"locked_{remaining}"
        else:
            # Lock expire ho gaya — reset karo
            c.execute("""
                UPDATE users SET failed_attempts = 0,
                locked_until = NULL WHERE username = ?
            """, (username,))
            conn.commit()

    # Password check
    if user["password_hash"] != hash_password(password):
        new_attempts = user["failed_attempts"] + 1

        if new_attempts >= 4:
            # 5 minute block
            lock_time = datetime.now() + timedelta(minutes=5)
            c.execute("""
                UPDATE users SET failed_attempts = ?,
                locked_until = ? WHERE username = ?
            """, (new_attempts, lock_time.isoformat(), username))
            conn.commit()
            conn.close()
            return False, "account_locked"
        else:
            remaining_attempts = 4 - new_attempts
            c.execute("""
                UPDATE users SET failed_attempts = ?
                WHERE username = ?
            """, (new_attempts, username))
            conn.commit()
            conn.close()
            return False, f"wrong_password_{remaining_attempts}"

    # Login success — reset attempts
    c.execute("""
        UPDATE users SET failed_attempts = 0,
        locked_until = NULL WHERE username = ?
    """, (username,))
    conn.commit()
    conn.close()
    return True, "success"

def change_password(username, old_password, new_password):
    """Password change karo"""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT password_hash FROM users WHERE username = ?",
              (username,))
    user = c.fetchone()

    if not user or user["password_hash"] != hash_password(old_password):
        conn.close()
        return False, "wrong_password"

    strength_errors = check_password_strength(new_password)
    if strength_errors:
        conn.close()
        return False, strength_errors

    c.execute("""
        UPDATE users SET password_hash = ? WHERE username = ?
    """, (hash_password(new_password), username))
    conn.commit()
    conn.close()
    return True, "success"

def reset_pin_secret_question(username, answer, new_password):
    """Secret question se password reset karo"""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT secret_question, secret_answer FROM users
        WHERE username = ?
    """, (username,))
    user = c.fetchone()

    if not user:
        conn.close()
        return False, "user_not_found", None

    if user["secret_answer"] != hash_answer(answer):
        conn.close()
        return False, "wrong_answer", None

    strength_errors = check_password_strength(new_password)
    if strength_errors:
        conn.close()
        return False, strength_errors, None

    c.execute("""
        UPDATE users SET password_hash = ?,
        failed_attempts = 0, locked_until = NULL
        WHERE username = ?
    """, (hash_password(new_password), username))
    conn.commit()
    conn.close()
    return True, "success", None

def reset_pin_admin(username, admin_password, new_password,
                    admin_secret):
    """Admin password se reset karo"""
    if admin_password != admin_secret:
        return False, "wrong_admin_password"

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT username FROM users WHERE username = ?",
              (username,))
    if not c.fetchone():
        conn.close()
        return False, "user_not_found"

    strength_errors = check_password_strength(new_password)
    if strength_errors:
        conn.close()
        return False, strength_errors

    c.execute("""
        UPDATE users SET password_hash = ?,
        failed_attempts = 0, locked_until = NULL
        WHERE username = ?
    """, (hash_password(new_password), username))
    conn.commit()
    conn.close()
    return True, "success"

def get_secret_question(username):
    """User ka secret question laao"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT secret_question FROM users WHERE username = ?
    """, (username,))
    user = c.fetchone()
    conn.close()
    if user:
        return user["secret_question"]
    return None

def get_user_settings(username):
    """User settings laao"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM settings WHERE username = ?
    """, (username,))
    settings = c.fetchone()
    conn.close()
    if settings:
        result = dict(settings)
        if "savings_goal" not in result:
            result["savings_goal"] = 30
        return result
    return {"currency_symbol": "Rs.", "savings_goal": 30}

def save_user_settings(username, currency_symbol, savings_goal=30):
    """User settings save karo"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO settings
        (username, currency_symbol, savings_goal)
        VALUES (?, ?, ?)
    """, (username, currency_symbol, savings_goal))
    conn.commit()
    conn.close()

def get_budgets(username):
    """User budgets laao"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT category, amount FROM budgets
        WHERE username = ? OR username = 'default'
        ORDER BY username DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    budgets = {}
    for row in rows:
        if row["category"] not in budgets:
            budgets[row["category"]] = row["amount"]
    return budgets

def save_budgets(username, budgets_dict):
    """User budgets save karo"""
    conn = get_connection()
    c = conn.cursor()
    for cat, amt in budgets_dict.items():
        c.execute("""
            INSERT OR REPLACE INTO budgets (username, category, amount)
            VALUES (?, ?, ?)
        """, (username, cat, amt))
    conn.commit()
    conn.close()

# ── EXPENSES ─────────────────────────────────────────────
def add_expense(username, date, category, description, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO expenses
        (username, date, category, description, amount)
        VALUES (?, ?, ?, ?, ?)
    """, (username, str(date), category, description, float(amount)))
    conn.commit()
    conn.close()

def get_expenses(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT rowid as id, date, category, description, amount
        FROM expenses WHERE username = ?
        ORDER BY date DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    import pandas as pd
    if not rows:
        return pd.DataFrame(
            columns=["id", "date", "category",
                     "description", "amount"])
    df = pd.DataFrame([dict(r) for r in rows])
    df.columns = ["id", "Date", "Category", "Description", "Amount"]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return df

def update_expense(expense_id, date, category, description, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE expenses SET date=?, category=?,
        description=?, amount=? WHERE rowid=?
    """, (str(date), category, description,
          float(amount), expense_id))
    conn.commit()
    conn.close()

def delete_expense(expense_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE rowid=?", (expense_id,))
    conn.commit()
    conn.close()

# ── INCOME ────────────────────────────────────────────────
def add_income(username, date, source, description, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO income
        (username, date, source, description, amount)
        VALUES (?, ?, ?, ?, ?)
    """, (username, str(date), source, description, float(amount)))
    conn.commit()
    conn.close()

def get_income(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT rowid as id, date, source, description, amount
        FROM income WHERE username = ?
        ORDER BY date DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    import pandas as pd
    if not rows:
        return pd.DataFrame(
            columns=["id", "date", "source",
                     "description", "amount"])
    df = pd.DataFrame([dict(r) for r in rows])
    df.columns = ["id", "Date", "Source", "Description", "Amount"]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return df

def update_income(income_id, date, source, description, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE income SET date=?, source=?,
        description=?, amount=? WHERE rowid=?
    """, (str(date), source, description,
          float(amount), income_id))
    conn.commit()
    conn.close()

def delete_income(income_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM income WHERE rowid=?", (income_id,))
    conn.commit()
    conn.close()