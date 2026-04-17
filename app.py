import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import sys
import os

# ── Import your agent modules ──────────────────────────────────────────────────
# Make sure all files are in the same folder:
# scrape_jd.py, rewrite_bullets.py, job_tracker.py, telegram_alerts.py

sys.path.append(os.path.dirname(__file__))

from job_tracker import (
    init_db, add_application, update_status,
    get_all_applications, get_stats,
    get_pending_followups, mark_alert_sent
)
from scrape_jd import scrape_job_description
from rewrite_bullets import rewrite_bullets, BASE_BULLETS
from telegram_alerts import run_daily_check, test_connection

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Job Agent — Sanjai J",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Init DB ────────────────────────────────────────────────────────────────────
init_db()

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-num  { font-size: 32px; font-weight: 700; color: #1a56db; margin: 0; }
.metric-lbl  { font-size: 13px; color: #64748b; margin: 0; }
.status-Applied   { color: #1a56db; font-weight: 600; }
.status-Interview { color: #059669; font-weight: 600; }
.status-Offer     { color: #7c3aed; font-weight: 600; }
.status-Rejected  { color: #dc2626; font-weight: 600; }
.status-Ghosted   { color: #92400e; font-weight: 600; }
.status-Viewed    { color: #0284c7; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI Job Agent")
    st.markdown("**Sanjai J** — AI/ML Engineer")
    st.divider()

    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "➕ Apply to Job", "📋 All Applications", "🔔 Follow-ups"],
        label_visibility="collapsed"
    )

    st.divider()

    if st.button("🔔 Run Follow-up Check", use_container_width=True):
        with st.spinner("Checking follow-ups..."):
            try:
                run_daily_check()
                st.success("Alerts sent via Telegram!")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🧪 Test Telegram Bot", use_container_width=True):
        with st.spinner("Sending test..."):
            try:
                test_connection()
                st.success("Test message sent!")
            except Exception as e:
                st.error(f"Check your bot token & chat ID: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.title("📊 Job Application Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

    stats = get_stats()

    # Metrics row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    metrics = [
        (c1, stats["total"],      "Total Applied"),
        (c2, stats["pending"],    "Awaiting Reply"),
        (c3, stats["interviews"], "Interviews"),
        (c4, stats["offers"],     "Offers"),
        (c5, stats["rejected"],   "Rejected"),
        (c6, stats["ghosted"],    "Ghosted"),
    ]
    for col, num, label in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-num">{num}</p>
                <p class="metric-lbl">{label}</p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Recent applications table
    st.subheader("Recent Applications")
    apps = get_all_applications()

    if not apps:
        st.info("No applications yet. Go to 'Apply to Job' to log your first one.")
    else:
        df = pd.DataFrame(apps, columns=[
            "ID", "Company", "Role", "Status",
            "Applied Date", "Follow-up Date", "Job URL"
        ])
        st.dataframe(
            df[["ID", "Company", "Role", "Status", "Applied Date", "Follow-up Date"]],
            use_container_width=True,
            hide_index=True,
        )

    # Follow-ups due
    followups = get_pending_followups()
    if followups:
        st.divider()
        st.subheader(f"⚠️ Follow-ups Due ({len(followups)})")
        for f in followups:
            app_id, company, role, job_url, applied_date = f
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{role}** at **{company}** — applied {applied_date}")
            with col2:
                if st.button("Mark Sent", key=f"fu_{app_id}"):
                    mark_alert_sent(app_id)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — APPLY TO JOB (Full AI pipeline)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Apply to Job":
    st.title("➕ Apply to a Job")
    st.caption("Paste a job URL — the agent scrapes it, rewrites your bullets, and logs the application.")

    # Step 1: URL input
    st.subheader("Step 1 — Paste Job URL")
    job_url = st.text_input("Job posting URL", placeholder="https://naukri.com/job-listings-...")

    col1, col2 = st.columns(2)
    with col1:
        company = st.text_input("Company name", placeholder="Zoho Corporation")
    with col2:
        role = st.text_input("Role title", placeholder="AI Engineer")

    notes = st.text_input("Notes (optional)", placeholder="Applied via LinkedIn Easy Apply")

    # Step 2: Scrape & Rewrite
    if st.button("🤖 Scrape JD & Rewrite Bullets", type="primary", use_container_width=True):
        if not job_url:
            st.warning("Please paste a job URL first.")
        elif not company or not role:
            st.warning("Please enter company name and role.")
        else:
            # Scrape
            with st.spinner("Scraping job description..."):
                jd_result = scrape_job_description(job_url)

            if not jd_result["success"]:
                st.error(f"Could not scrape: {jd_result['error']}")
                st.info("You can still log the application manually below.")
            else:
                st.success(f"Scraped {len(jd_result['text'])} characters from {jd_result['site']}")

                # Show JD preview
                with st.expander("View scraped job description"):
                    st.text(jd_result["text"][:1500] + "...")

                # Rewrite bullets
                with st.spinner("Rewriting resume bullets with Groq AI..."):
                    try:
                        rewrite_result = rewrite_bullets(jd_result["text"], BASE_BULLETS)

                        st.subheader("🎯 Top ATS Keywords from This JD")
                        keyword_cols = st.columns(5)
                        for i, kw in enumerate(rewrite_result["keywords"]):
                            with keyword_cols[i % 5]:
                                st.markdown(f"`{kw}`")

                        st.subheader("✏️ Rewritten Resume Bullets")
                        st.caption("Copy these into your resume before applying.")
                        for i, bullet in enumerate(rewrite_result["rewritten_bullets"], 1):
                            st.markdown(f"**{i}.** {bullet}")

                        # Save keywords to session for logging
                        st.session_state["keywords"] = rewrite_result["keywords"]
                        st.session_state["jd_scraped"] = True

                    except Exception as e:
                        st.error(f"Groq API error: {e}")
                        st.info("Check your GROQ_API_KEY environment variable.")

    # Step 3: Log application
    st.divider()
    st.subheader("Step 2 — Log This Application")

    if st.button("✅ Log Application to Tracker", use_container_width=True):
        if not company or not role:
            st.warning("Enter company and role first.")
        else:
            keywords = st.session_state.get("keywords", [])
            app_id = add_application(
                company=company,
                role=role,
                job_url=job_url,
                keywords=keywords,
                notes=notes
            )
            st.success(f"Application logged! ID: {app_id} — Follow-up reminder set for 7 days.")
            st.balloons()
            # Clear session
            st.session_state["keywords"] = []
            st.session_state["jd_scraped"] = False

    # Manual JD input fallback
    st.divider()
    st.subheader("Can't scrape? Paste JD manually")
    manual_jd = st.text_area("Paste the job description text here", height=200)
    manual_company = st.text_input("Company", key="m_company")
    manual_role    = st.text_input("Role", key="m_role")

    if st.button("🤖 Rewrite from Manual JD", use_container_width=True):
        if manual_jd and manual_company and manual_role:
            with st.spinner("Rewriting bullets..."):
                try:
                    result = rewrite_bullets(manual_jd, BASE_BULLETS)
                    st.subheader("✏️ Rewritten Bullets")
                    for i, b in enumerate(result["rewritten_bullets"], 1):
                        st.markdown(f"**{i}.** {b}")
                    st.subheader("🎯 Keywords")
                    st.write(", ".join(result["keywords"]))
                    app_id = add_application(
                        company=manual_company,
                        role=manual_role,
                        keywords=result["keywords"]
                    )
                    st.success(f"Logged! Application ID: {app_id}")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Fill in company, role, and JD text.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — ALL APPLICATIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 All Applications":
    st.title("📋 All Applications")

    apps = get_all_applications()

    if not apps:
        st.info("No applications logged yet.")
    else:
        df = pd.DataFrame(apps, columns=[
            "ID", "Company", "Role", "Status",
            "Applied Date", "Follow-up Date", "Job URL"
        ])

        # Filter by status
        statuses = ["All"] + list(df["Status"].unique())
        selected = st.selectbox("Filter by status", statuses)
        if selected != "All":
            df = df[df["Status"] == selected]

        st.caption(f"Showing {len(df)} application(s)")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Update status
        st.divider()
        st.subheader("Update Application Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            app_id_input = st.number_input("Application ID", min_value=1, step=1)
        with col2:
            new_status = st.selectbox(
                "New Status",
                ["Applied", "Viewed", "Interview", "Offer", "Rejected", "Ghosted"]
            )
        with col3:
            st.write("")
            st.write("")
            if st.button("Update", use_container_width=True):
                update_status(int(app_id_input), new_status)
                st.success(f"Updated #{app_id_input} → {new_status}")
                st.rerun()

        # Export
        st.divider()
        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️ Export as CSV",
            data=csv,
            file_name=f"applications_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — FOLLOW-UPS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔔 Follow-ups":
    st.title("🔔 Follow-up Reminders")
    st.caption("Applications with no reply after 7 days.")

    followups = get_pending_followups()

    if not followups:
        st.success("You're all caught up — no follow-ups due today.")
    else:
        st.warning(f"{len(followups)} application(s) need a follow-up today.")

        for f in followups:
            app_id, company, role, job_url, applied_date = f
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"**{role}** at **{company}**")
                    st.caption(f"Applied: {applied_date}")
                with c2:
                    if job_url:
                        st.markdown(f"[View Job Posting]({job_url})")
                with c3:
                    if st.button("✅ Done", key=f"done_{app_id}"):
                        mark_alert_sent(app_id)
                        update_status(app_id, "Ghosted")
                        st.rerun()
                st.divider()

        if st.button("📨 Send All Alerts via Telegram", type="primary", use_container_width=True):
            with st.spinner("Sending Telegram alerts..."):
                run_daily_check()
            st.success("All alerts sent!")
            st.rerun()