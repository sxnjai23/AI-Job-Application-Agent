import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "job_tracker.db"


# ── Setup ──────────────────────────────────────────────────────────────────────

def init_db():
    """Create the database and table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company         TEXT NOT NULL,
            role            TEXT NOT NULL,
            job_url         TEXT,
            applied_date    TEXT NOT NULL,
            status          TEXT DEFAULT 'Applied',
            follow_up_date  TEXT,
            alert_sent      INTEGER DEFAULT 0,
            keywords        TEXT,
            notes           TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database ready: {DB_PATH}")


# ── Core operations ────────────────────────────────────────────────────────────

def add_application(company, role, job_url="", keywords=None, notes=""):
    """
    Log a new job application.
    Returns the new row ID.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    applied_date   = datetime.now().strftime("%Y-%m-%d")
    follow_up_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    keywords_str   = ", ".join(keywords) if keywords else ""

    c.execute("""
        INSERT INTO applications
            (company, role, job_url, applied_date, follow_up_date, keywords, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (company, role, job_url, applied_date, follow_up_date, keywords_str, notes))

    new_id = c.lastrowid
    conn.commit()
    conn.close()

    print(f"Logged: [{new_id}] {role} at {company} — follow-up on {follow_up_date}")
    return new_id


def update_status(app_id, status):
    """
    Update application status.
    Status options: Applied, Viewed, Interview, Offer, Rejected, Ghosted
    """
    valid = {"Applied", "Viewed", "Interview", "Offer", "Rejected", "Ghosted"}
    if status not in valid:
        print(f"Invalid status. Choose from: {valid}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
    conn.commit()
    conn.close()
    print(f"Updated [{app_id}] → {status}")


def get_pending_followups():
    """
    Return applications where:
    - follow_up_date is today or earlier
    - status is still 'Applied' (no response)
    - alert not already sent
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT id, company, role, job_url, applied_date
        FROM applications
        WHERE follow_up_date <= ?
          AND status = 'Applied'
          AND alert_sent = 0
    """, (today,))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_alert_sent(app_id):
    """Mark that a Telegram alert was sent for this application."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE applications SET alert_sent = 1 WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_all_applications():
    """Return all applications ordered by most recent."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, company, role, status, applied_date, follow_up_date, job_url
        FROM applications
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def get_stats():
    """Return summary stats for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM applications")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Applied'")
    pending = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Interview'")
    interviews = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Offer'")
    offers = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Rejected'")
    rejected = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Ghosted'")
    ghosted = c.fetchone()[0]

    conn.close()

    return {
        "total":      total,
        "pending":    pending,
        "interviews": interviews,
        "offers":     offers,
        "rejected":   rejected,
        "ghosted":    ghosted,
    }


def print_all():
    """Print all applications in a readable table."""
    apps = get_all_applications()
    if not apps:
        print("No applications logged yet.")
        return

    print(f"\n{'ID':<4} {'Company':<22} {'Role':<28} {'Status':<12} {'Applied':<12} {'Follow-up'}")
    print("-" * 90)
    for row in apps:
        id_, company, role, status, applied, followup, url = row
        print(f"{id_:<4} {company[:20]:<22} {role[:26]:<28} {status:<12} {applied:<12} {followup}")


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    # Add a test application
    add_application(
        company="Zoho Corporation",
        role="AI Engineer",
        job_url="https://careers.zoho.com/example",
        keywords=["Python", "Machine Learning", "NLP", "FastAPI"],
        notes="Applied via careers page. Resume v4 used."
    )

    add_application(
        company="Freshworks",
        role="ML Engineer",
        job_url="https://freshworks.com/careers/example",
        keywords=["Deep Learning", "TensorFlow", "CNN", "Deployment"],
        notes="LinkedIn Easy Apply."
    )

    add_application(
        company="Sarvam AI",
        role="GenAI Developer",
        job_url="https://sarvam.ai/careers/example",
        keywords=["LLM", "RAG", "LangChain", "Hugging Face"],
        notes="Sent cold message to hiring manager on LinkedIn."
    )

    # Show all
    print_all()

    # Show stats
    stats = get_stats()
    print(f"\nStats: {stats['total']} total  |  "
          f"{stats['pending']} pending  |  "
          f"{stats['interviews']} interviews  |  "
          f"{stats['offers']} offers")

    # Simulate updating a status
    update_status(1, "Interview")

    # Check who needs a follow-up today
    followups = get_pending_followups()
    print(f"\nFollow-ups due: {len(followups)}")
    for f in followups:
        print(f"  → [{f[0]}] {f[2]} at {f[1]} — applied {f[4]}")