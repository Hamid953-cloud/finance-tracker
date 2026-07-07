import csv
import os
from datetime import datetime

DATA_FILE = os.path.join("data", "expenses.csv")

def ensure_csv_exists():
    """Agar CSV file ya folder na ho to bana dega"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Category", "Description", "Amount"])

def add_expense(category, description, amount):
    """Ek nayi expense CSV file mein add karega"""
    ensure_csv_exists()
    date_today = datetime.now().strftime("%Y-%m-%d")
    with open(DATA_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([date_today, category, description, amount])
    print(f"Expense add ho gaya: {category} - {description} - Rs.{amount}")

def show_summary():
    """Category-wise total kharcha dikhayega"""
    ensure_csv_exists()
    totals = {}
    with open(DATA_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Amount") or not row.get("Category"):
                continue
            try:
                amt = float(row["Amount"])
            except ValueError:
                continue
            cat = row["Category"]
            totals[cat] = totals.get(cat, 0) + amt

    print("\n=== Category-wise Summary ===")
    if not totals:
        print("Abhi tak koi expense nahi hai.")
    else:
        for cat, total in totals.items():
            print(f"{cat}: Rs.{total:.2f}")
    print("--------------------------")
    print(f"Total kharcha: Rs.{sum(totals.values()):.2f}\n")

def main_menu():
    while True:
        print("\n=== Personal Finance Tracker ===")
        print("1. Naya expense add karein")
        print("2. Summary dekhein")
        print("3. Exit")
        choice = input("Choice (1/2/3): ")

        if choice == "1":
            category = input("Category (jaise Food, Travel, Bills): ")
            description = input("Description (jaise 'Lunch'): ")
            amount = input("Amount (rupay mein): ")
            add_expense(category, description, amount)
        elif choice == "2":
            show_summary()
        elif choice == "3":
            print("Allah Hafiz!")
            break
        else:
            print("Galat choice, dobara try karein.")

if __name__ == "__main__":
    main_menu()