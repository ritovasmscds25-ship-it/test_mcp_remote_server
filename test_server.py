from datetime import datetime
import json
import os
import sqlite3

from fastmcp import FastMCP

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

mcp = FastMCP(name="Expense Tracker")


def load_categories():
    """Load and validate the category catalogue."""
    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as file:
            categories = json.load(file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Category file not found: {CATEGORIES_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {CATEGORIES_PATH}: {exc}") from exc

    if not isinstance(categories, dict) or not categories:
        raise ValueError("categories.json must contain a non-empty JSON object.")
    for category, subcategories in categories.items():
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Category names must be non-empty strings.")
        if not isinstance(subcategories, list) or not all(
            isinstance(item, str) and item.strip() for item in subcategories
        ):
            raise ValueError(f"Subcategories for {category!r} must be a list of strings.")
    return categories


def canonical_choice(value, choices, field_name):
    """Match case-insensitively but store the exact catalogue spelling."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    for choice in choices:
        if value.strip().casefold() == choice.casefold():
            return choice
    raise ValueError(f"Invalid {field_name} {value!r}. Allowed values: {choices}")


def validate_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError("Dates must use YYYY-MM-DD format.") from exc


def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                date TEXT NOT NULL,
                subcategory TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT ''
            )
        """)


init_db()


@mcp.tool
def get_categories():
    """
    Return the categories and subcategories from categories.json.
    Call this before recording an expense. Select the best matching labels
    from this list; do not invent category or subcategory names.
    """
    return load_categories()


@mcp.tool
def add_expense(date, amount, category, subcategory="", note=""):
    """
    Add an expense. First call get_categories, then choose the closest
    category and subcategory from that catalogue. The server validates both.
    Leave subcategory blank only when no listed subcategory is appropriate.
    """
    validate_date(date)
    try:
        amount = float(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("amount must be numeric.") from exc
    if amount <= 0:
        raise ValueError("amount must be greater than zero.")

    categories = load_categories()
    category = canonical_choice(category, list(categories), "category")
    if subcategory:
        subcategory = canonical_choice(
            subcategory, categories[category], "subcategory"
        )

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
        """, (date, amount, category, subcategory, note or ""))
    return {"status": "ok", "id": cursor.lastrowid}


@mcp.tool
def list_expenses(start_date, end_date):
    """List expenses between two inclusive YYYY-MM-DD dates."""
    validate_date(start_date)
    validate_date(end_date)
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date, id
        """, (start_date, end_date))
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@mcp.tool
def summarize(start_date, end_date, category=None):
    """Return total spending by category for an inclusive date range."""
    validate_date(start_date)
    validate_date(end_date)
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    query = """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if category:
        category = canonical_choice(category, list(load_categories()), "category")
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY category ASC"

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(query, params)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
