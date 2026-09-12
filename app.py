import os
import json
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask("MYSPLIT")
app.config["SECRET_KEY"] = "mysplit-demo-secret-key"
app.config["DATABASE"] = os.path.join(app.root_path, "expensewise.db")

CATEGORIES = [
    "Food",
    "Transportation",
    "Shopping",
    "Bills",
    "Entertainment",
    "Health",
    "Education",
    "Other",
]


def get_db():
    import sqlite3

    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                monthly_budget REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date)"
        )
        conn.commit()


@app.before_request
def setup_db():
    if not os.path.exists(app.config["DATABASE"]):
        init_db()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def format_money(value):
    # Format a number as Indian Rupees with rupee sign and Indian grouping (lakhs/crores)
    try:
        v = float(value or 0)
    except Exception:
        v = 0.0
    sign = "-" if v < 0 else ""
    v = abs(v)
    # Split integer and decimal parts
    int_part = str(int(v))
    dec_part = f"{v:.2f}".split(".")[1]

    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        grouped_int = ",".join(groups + [last3])
    else:
        grouped_int = int_part

    return f"₹{sign}{grouped_int}.{dec_part}"


def month_range_for_current_month():
    today = datetime.now()
    start = today.replace(day=1).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    return start, end


def get_monthly_summary(user_id, months=6):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date) AS month_key,
               strftime('%b', date) AS label,
               ROUND(COALESCE(SUM(amount), 0), 2) AS total
        FROM expenses
        WHERE user_id = ?
          AND date >= date('now', '-' || ? || ' months', 'start of month')
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month_key ASC
        """,
        (user_id, months - 1),
    ).fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({"label": row["label"], "total": float(row["total"] or 0)})
    return result


def get_category_totals(user_id, month_start=None, month_end=None):
    conn = get_db()
    if month_start and month_end:
        rows = conn.execute(
            """
            SELECT category, ROUND(COALESCE(SUM(amount), 0), 2) AS total
            FROM expenses
            WHERE user_id = ? AND date(date) >= date(?) AND date(date) <= date(?)
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id, month_start, month_end),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT category, ROUND(COALESCE(SUM(amount), 0), 2) AS total
            FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC
            """,
            (user_id,),
        ).fetchall()
    conn.close()

    return [
        {"category": row["category"], "total": float(row["total"] or 0)} for row in rows
    ]


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all registration fields.", "danger")
            return render_template("register.html")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "warning")
            conn.close()
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, monthly_budget) VALUES (?, ?, ?, 0)",
            (name, email, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        session["user_id"] = user_id
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("You are now logged in.", "success")
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    conn = get_db()
    month_start, month_end = month_range_for_current_month()

    total_spending = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = ? AND date(date) >= date(?) AND date(date) <= date(?)
        """,
        (user["id"], month_start, month_end),
    ).fetchone()["total"]

    expense_count = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM expenses
        WHERE user_id = ? AND date(date) >= date(?) AND date(date) <= date(?)
        """,
        (user["id"], month_start, month_end),
    ).fetchone()["count"]

    recent_expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5",
        (user["id"],),
    ).fetchall()

    category_totals = get_category_totals(user["id"], month_start, month_end)
    monthly_budget = float(user["monthly_budget"] or 0)
    remaining = monthly_budget - float(total_spending or 0)
    budget_warning = monthly_budget > 0 and remaining < 0
    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        total_spending=float(total_spending or 0),
        monthly_budget=monthly_budget,
        remaining=remaining,
        expense_count=expense_count,
        recent_expenses=recent_expenses,
        category_totals=category_totals,
        budget_warning=budget_warning,
        format_money=format_money,
    )


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        amount = float(request.form.get("amount", 0) or 0)
        category = request.form.get("category", "Other").strip()
        description = request.form.get("description", "").strip()
        expense_date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")

        if amount <= 0 or not description:
            flash("Amount must be greater than zero and description is required.", "danger")
            return render_template("expenses.html", categories=CATEGORIES, expense=None)

        if category not in CATEGORIES:
            category = "Other"

        conn = get_db()
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (current_user()["id"], amount, category, description, expense_date),
        )
        conn.commit()
        conn.close()

        flash("Expense added successfully.", "success")
        return redirect(url_for("expenses"))

    return render_template("expenses.html", categories=CATEGORIES, expense=None)


@app.route("/expenses")
@login_required
def expenses():
    user = current_user()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()
    return render_template(
        "expenses.html",
        expenses=rows,
        categories=CATEGORIES,
        format_money=format_money,
        expense=None,
    )


@app.route("/expense/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    user = current_user()
    conn = get_db()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user["id"]),
    ).fetchone()
    if not expense:
        flash("Expense not found.", "warning")
        return redirect(url_for("expenses"))

    if request.method == "POST":
        amount = float(request.form.get("amount", 0) or 0)
        category = request.form.get("category", "Other").strip()
        description = request.form.get("description", "").strip()
        expense_date = request.form.get("date") or expense["date"]

        if amount <= 0 or not description:
            flash("Amount must be greater than zero and description is required.", "danger")
            return render_template("expenses.html", categories=CATEGORIES, expense=expense, format_money=format_money)

        if category not in CATEGORIES:
            category = "Other"

        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, description = ?, date = ? WHERE id = ? AND user_id = ?",
            (amount, category, description, expense_date, expense_id, user["id"]),
        )
        conn.commit()
        conn.close()
        flash("Expense updated successfully.", "success")
        return redirect(url_for("expenses"))

    conn.close()
    return render_template("expenses.html", categories=CATEGORIES, expense=expense, format_money=format_money)


@app.route("/expense/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id):
    user = current_user()
    conn = get_db()
    conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user["id"]),
    )
    conn.commit()
    conn.close()
    flash("Expense deleted.", "info")
    return redirect(url_for("expenses"))


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    user = current_user()

    if request.method == "POST":
        monthly_budget = float(request.form.get("monthly_budget", 0) or 0)
        conn = get_db()
        conn.execute(
            "UPDATE users SET monthly_budget = ? WHERE id = ?",
            (monthly_budget, user["id"]),
        )
        conn.commit()
        conn.close()
        flash("Monthly budget updated successfully.", "success")
        return redirect(url_for("budget"))

    month_start, month_end = month_range_for_current_month()
    conn = get_db()
    total_spending = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? AND date(date) >= date(?) AND date(date) <= date(?)",
        (user["id"], month_start, month_end),
    ).fetchone()["total"]
    conn.close()

    remaining = float(user["monthly_budget"] or 0) - float(total_spending or 0)
    budget_warning = float(user["monthly_budget"] or 0) > 0 and remaining < 0
    return render_template(
        "budget.html",
        user=user,
        monthly_budget=float(user["monthly_budget"] or 0),
        total_spending=float(total_spending or 0),
        remaining=remaining,
        budget_warning=budget_warning,
        format_money=format_money,
    )


@app.route("/reports")
@login_required
def reports():
    user = current_user()
    month_start, month_end = month_range_for_current_month()
    monthly_summary = get_monthly_summary(user["id"], months=6)
    current_category_totals = get_category_totals(user["id"], month_start, month_end)

    chart_labels = [entry["label"] for entry in monthly_summary]
    chart_values = [float(entry["total"]) for entry in monthly_summary]
    category_labels = [entry["category"] for entry in current_category_totals]
    category_values = [float(entry["total"]) for entry in current_category_totals]

    total_reported = sum(chart_values)
    largest_category = max(current_category_totals, key=lambda item: item["total"], default={"category": "None", "total": 0})

    return render_template(
        "reports.html",
        monthly_summary=monthly_summary,
        current_category_totals=current_category_totals,
        chart_labels=json.dumps(chart_labels),
        chart_values=json.dumps(chart_values),
        category_labels=json.dumps(category_labels),
        category_values=json.dumps(category_values),
        total_reported=total_reported,
        largest_category=largest_category,
        format_money=format_money,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
