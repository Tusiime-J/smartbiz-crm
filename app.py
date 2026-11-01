from datetime import date, datetime
from pathlib import Path
import os
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("SMARTBIZ_DATABASE", BASE_DIR / "smartbiz.db"))

app = Flask(
    __name__,
    template_folder="smartbiz_crm/templates",
    static_folder="smartbiz_crm/static"
)
app.config["SECRET_KEY"] = os.environ.get("SMARTBIZ_SECRET_KEY", "change-this-development-key")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL DEFAULT '',
        email TEXT NOT NULL DEFAULT '',
        business TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        title TEXT NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        stage TEXT NOT NULL DEFAULT 'Lead'
            CHECK(stage IN ('Lead','Proposal','Negotiation','Won','Lost')),
        expected_date TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        title TEXT NOT NULL,
        due_date TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '',
        completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
    );
    """)
    db.commit()
    db.close()


@app.template_filter("ugx")
def ugx(value):
    try:
        return "UGX {:,.0f}".format(float(value or 0))
    except (TypeError, ValueError):
        return "UGX 0"


@app.context_processor
def inject_globals():
    return {"today": date.today().isoformat()}


def customer_or_404(customer_id):
    row = get_db().execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if row is None:
        abort(404)
    return row


@app.route("/")
def dashboard():
    db = get_db()
    customer_count = db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    sales_total = db.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE stage='Won'").fetchone()[0]
    pipeline_total = db.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE stage NOT IN ('Won','Lost')").fetchone()[0]
    open_followups = db.execute("SELECT COUNT(*) FROM followups WHERE completed=0").fetchone()[0]
    overdue = db.execute("SELECT COUNT(*) FROM followups WHERE completed=0 AND due_date < ?", (date.today().isoformat(),)).fetchone()[0]
    recent_sales = db.execute("""
        SELECT s.*, c.name AS customer_name FROM sales s
        LEFT JOIN customers c ON c.id=s.customer_id
        ORDER BY s.created_at DESC, s.id DESC LIMIT 6
    """).fetchall()
    upcoming = db.execute("""
        SELECT f.*, c.name AS customer_name FROM followups f
        LEFT JOIN customers c ON c.id=f.customer_id
        WHERE f.completed=0 ORDER BY f.due_date ASC, f.id DESC LIMIT 6
    """).fetchall()
    return render_template("dashboard.html", customer_count=customer_count,
        sales_total=sales_total, pipeline_total=pipeline_total,
        open_followups=open_followups, overdue=overdue,
        recent_sales=recent_sales, upcoming=upcoming)


@app.route("/customers")
def customers():
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        rows = get_db().execute("""
            SELECT * FROM customers
            WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? OR business LIKE ?
            ORDER BY name COLLATE NOCASE
        """, (like, like, like, like)).fetchall()
    else:
        rows = get_db().execute("SELECT * FROM customers ORDER BY name COLLATE NOCASE").fetchall()
    return render_template("customers.html", customers=rows, q=q)


@app.route("/customers/new", methods=["GET", "POST"])
def customer_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Customer name is required.", "error")
            return render_template("customer_form.html", customer=None)
        db = get_db()
        db.execute("""INSERT INTO customers (name, phone, email, business, notes)
                      VALUES (?, ?, ?, ?, ?)""",
                   (name, request.form.get("phone", "").strip(),
                    request.form.get("email", "").strip(),
                    request.form.get("business", "").strip(),
                    request.form.get("notes", "").strip()))
        db.commit()
        flash("Customer added successfully.", "success")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=None)


@app.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
def customer_edit(customer_id):
    customer = customer_or_404(customer_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Customer name is required.", "error")
            return render_template("customer_form.html", customer=customer)
        db = get_db()
        db.execute("""UPDATE customers SET name=?, phone=?, email=?, business=?, notes=?
                      WHERE id=?""",
                   (name, request.form.get("phone", "").strip(),
                    request.form.get("email", "").strip(),
                    request.form.get("business", "").strip(),
                    request.form.get("notes", "").strip(), customer_id))
        db.commit()
        flash("Customer details updated.", "success")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=customer)


@app.post("/customers/<int:customer_id>/delete")
def customer_delete(customer_id):
    customer_or_404(customer_id)
    db = get_db()
    db.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    db.commit()
    flash("Customer deleted. Related sales and follow-ups were retained without a customer link.", "success")
    return redirect(url_for("customers"))


@app.route("/sales")
def sales():
    rows = get_db().execute("""
        SELECT s.*, c.name AS customer_name FROM sales s
        LEFT JOIN customers c ON c.id=s.customer_id
        ORDER BY s.created_at DESC, s.id DESC
    """).fetchall()
    totals = get_db().execute("""
        SELECT stage, COALESCE(SUM(amount),0) AS total, COUNT(*) AS count
        FROM sales GROUP BY stage
    """).fetchall()
    return render_template("sales.html", sales=rows, totals={r["stage"]: r for r in totals},
                           stages=["Lead", "Proposal", "Negotiation", "Won", "Lost"])


@app.route("/sales/new", methods=["GET", "POST"])
def sale_new():
    db = get_db()
    customer_rows = db.execute("SELECT id, name FROM customers ORDER BY name").fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        try:
            amount = float(request.form.get("amount", "0"))
            if amount < 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid non-negative sales amount.", "error")
            return render_template("sale_form.html", customers=customer_rows, sale=None)
        if not title:
            flash("Opportunity title is required.", "error")
            return render_template("sale_form.html", customers=customer_rows, sale=None)
        customer_id = request.form.get("customer_id") or None
        stage = request.form.get("stage", "Lead")
        if stage not in ["Lead", "Proposal", "Negotiation", "Won", "Lost"]:
            stage = "Lead"
        db.execute("""INSERT INTO sales (customer_id,title,amount,stage,expected_date,notes)
                      VALUES (?,?,?,?,?,?)""",
                   (customer_id, title, amount, stage,
                    request.form.get("expected_date", "").strip(),
                    request.form.get("notes", "").strip()))
        db.commit()
        flash("Sales opportunity recorded.", "success")
        return redirect(url_for("sales"))
    return render_template("sale_form.html", customers=customer_rows, sale=None)


@app.post("/sales/<int:sale_id>/stage")
def sale_stage(sale_id):
    stage = request.form.get("stage", "")
    if stage not in ["Lead", "Proposal", "Negotiation", "Won", "Lost"]:
        abort(400)
    db = get_db()
    result = db.execute("UPDATE sales SET stage=? WHERE id=?", (stage, sale_id))
    if result.rowcount == 0:
        abort(404)
    db.commit()
    flash("Sales stage updated.", "success")
    return redirect(url_for("sales"))


@app.post("/sales/<int:sale_id>/delete")
def sale_delete(sale_id):
    db = get_db()
    result = db.execute("DELETE FROM sales WHERE id=?", (sale_id,))
    if result.rowcount == 0:
        abort(404)
    db.commit()
    flash("Sales opportunity deleted.", "success")
    return redirect(url_for("sales"))


@app.route("/followups")
def followups():
    rows = get_db().execute("""
        SELECT f.*, c.name AS customer_name FROM followups f
        LEFT JOIN customers c ON c.id=f.customer_id
        ORDER BY f.completed ASC, f.due_date ASC, f.id DESC
    """).fetchall()
    return render_template("followups.html", followups=rows)


@app.route("/followups/new", methods=["GET", "POST"])
def followup_new():
    db = get_db()
    customer_rows = db.execute("SELECT id, name FROM customers ORDER BY name").fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        due_date = request.form.get("due_date", "").strip()
        if not title or not due_date:
            flash("Task title and due date are required.", "error")
            return render_template("followup_form.html", customers=customer_rows)
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            flash("Enter a valid due date.", "error")
            return render_template("followup_form.html", customers=customer_rows)
        db.execute("""INSERT INTO followups (customer_id,title,due_date,notes)
                      VALUES (?,?,?,?)""",
                   (request.form.get("customer_id") or None, title, due_date,
                    request.form.get("notes", "").strip()))
        db.commit()
        flash("Follow-up task created.", "success")
        return redirect(url_for("followups"))
    return render_template("followup_form.html", customers=customer_rows)


@app.post("/followups/<int:followup_id>/toggle")
def followup_toggle(followup_id):
    db = get_db()
    row = db.execute("SELECT completed FROM followups WHERE id=?", (followup_id,)).fetchone()
    if row is None:
        abort(404)
    db.execute("UPDATE followups SET completed=? WHERE id=?",
               (0 if row["completed"] else 1, followup_id))
    db.commit()
    flash("Follow-up status updated.", "success")
    return redirect(url_for("followups"))


@app.post("/followups/<int:followup_id>/delete")
def followup_delete(followup_id):
    db = get_db()
    result = db.execute("DELETE FROM followups WHERE id=?", (followup_id,))
    if result.rowcount == 0:
        abort(404)
    db.commit()
    flash("Follow-up task deleted.", "success")
    return redirect(url_for("followups"))


@app.route("/reports")
def reports():
    db = get_db()
    by_stage = db.execute("""
        SELECT stage, COUNT(*) AS count, COALESCE(SUM(amount),0) AS total
        FROM sales GROUP BY stage ORDER BY
        CASE stage WHEN 'Lead' THEN 1 WHEN 'Proposal' THEN 2
        WHEN 'Negotiation' THEN 3 WHEN 'Won' THEN 4 ELSE 5 END
    """).fetchall()
    total_won = db.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE stage='Won'").fetchone()[0]
    total_pipeline = db.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE stage IN ('Lead','Proposal','Negotiation')").fetchone()[0]
    return render_template("reports.html", by_stage=by_stage, total_won=total_won,
                           total_pipeline=total_pipeline)


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
