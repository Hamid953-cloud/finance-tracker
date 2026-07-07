import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join("data", "finance.db")

def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Sab tables banao agar exist na karein"""
    conn = get_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            secret_question TEXT,
            secret_answer TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TEXT DEFAULT NULL
        )
    """)

    # Expenses table
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)

    # Income table
    c.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)

    # Budgets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            PRIMARY KEY (username, category),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)

    # Settings table
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            username TEXT PRIMARY KEY,
            currency_symbol TEXT DEFAULT 'Rs.',
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    # Settings table mein savings_goal column add karo (migration)
    try:
        c.execute("ALTER TABLE settings ADD COLUMN savings_goal REAL DEFAULT 30")
    except:
        pass  # Column already exists
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def migrate_csv_data():
    """Purani CSV files ka data SQLite mein migrate karo"""
    import pandas as pd
    import json

    conn = get_connection()
    c = conn.cursor()
    migrated = []

    # Expenses CSV migrate karo
    data_folder = "data"
    for file in os.listdir(data_folder):
        if file.startswith("expenses_") and file.endswith(".csv"):
            username = file.replace("expenses_", "").replace(".csv", "")
            filepath = os.path.join(data_folder, file)
            try:
                df = pd.read_csv(filepath)
                df = df.dropna(subset=["Amount", "Category"])
                df["Amount"] = pd.to_numeric(
                    df["Amount"], errors="coerce")
                df = df.dropna(subset=["Amount"])
                for _, row in df.iterrows():
                    c.execute("""
                        INSERT OR IGNORE INTO expenses
                        (username, date, category, description, amount)
                        VALUES (?, ?, ?, ?, ?)
                    """, (username, str(row["Date"]),
                          str(row["Category"]),
                          str(row["Description"]),
                          float(row["Amount"])))
                migrated.append(f"expenses_{username}")
            except Exception as e:
                print(f"Error migrating {file}: {e}")

    # Income CSV migrate karo
    for file in os.listdir(data_folder):
        if file.startswith("income_") and file.endswith(".csv"):
            username = file.replace("income_", "").replace(".csv", "")
            filepath = os.path.join(data_folder, file)
            try:
                df = pd.read_csv(filepath)
                df = df.dropna(subset=["Amount"])
                df["Amount"] = pd.to_numeric(
                    df["Amount"], errors="coerce")
                df = df.dropna(subset=["Amount"])
                for _, row in df.iterrows():
                    c.execute("""
                        INSERT OR IGNORE INTO income
                        (username, date, source, description, amount)
                        VALUES (?, ?, ?, ?, ?)
                    """, (username, str(row["Date"]),
                          str(row["Source"]),
                          str(row["Description"]),
                          float(row["Amount"])))
                migrated.append(f"income_{username}")
            except Exception as e:
                print(f"Error migrating {file}: {e}")

    # Budgets JSON migrate karo
    budgets_file = os.path.join(data_folder, "budgets.json")
    if os.path.exists(budgets_file):
        try:
            with open(budgets_file, "r") as f:
                budgets = json.load(f)
            for cat, amt in budgets.items():
                c.execute("""
                    INSERT OR REPLACE INTO budgets
                    (username, category, amount)
                    VALUES (?, ?, ?)
                """, ("default", cat, amt))
            migrated.append("budgets")
        except Exception as e:
            print(f"Error migrating budgets: {e}")

    conn.commit()
    conn.close()

    if migrated:
        print(f"✅ Migrated: {', '.join(migrated)}")
    else:
        print("No CSV data to migrate.")

if __name__ == "__main__":
    init_database()
    migrate_csv_data()
    print("✅ Database setup complete!")