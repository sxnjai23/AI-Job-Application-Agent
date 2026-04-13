import os
import requests
from job_tracker import get_pending_followups, mark_alert_sent, init_db

# ── Config ─────────────────────────────────────────────────────────────────────
# Get these from the setup steps below
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8294022580:AAExxrrG2GjrMynE4oyINf9vbZPFNzazAXI")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "1301574453")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ── Core send function ─────────────────────────────────────────────────────────

def send_message(text: str) -> bool:
    """Send a message to your Telegram chat."""
    url  = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",  # lets us use *bold* and formatting
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        result   = response.json()
        if result.get("ok"):
            return True
        else:
            print(f"Telegram error: {result.get('description')}")
            return False
    except Exception as e:
        print(f"Failed to send message: {e}")
        return False


def send_followup_alert(app_id, company, role, job_url, applied_date) -> bool:
    """Send a formatted follow-up reminder for one application."""
    job_link = f"[View Job]({job_url})" if job_url else "No URL saved"

    message = (
        f"📬 *Follow-up Reminder*\n\n"
        f"No reply after 7 days.\n\n"
        f"🏢 *Company:* {company}\n"
        f"💼 *Role:* {role}\n"
        f"📅 *Applied:* {applied_date}\n"
        f"🔗 {job_link}\n\n"
        f"*Action:* Send a follow-up email or LinkedIn message today."
    )
    return send_message(message)


# ── Daily check ────────────────────────────────────────────────────────────────

def run_daily_check():
    """
    Check database for applications with no reply after 7 days.
    Send a Telegram alert for each one, then mark alert as sent.
    Run this every day — via cron, Streamlit scheduler, or manually.
    """
    init_db()
    pending = get_pending_followups()

    if not pending:
        print("No follow-ups due today.")
        send_message("✅ *Daily Check Complete*\nNo follow-ups due today. Keep applying!")
        return

    # Send summary first
    send_message(
        f"🔔 *Daily Job Alert*\n\n"
        f"You have *{len(pending)} application(s)* with no reply after 7 days.\n"
        f"Time to follow up!"
    )

    # Send individual alerts
    success_count = 0
    for app in pending:
        app_id, company, role, job_url, applied_date = app
        sent = send_followup_alert(app_id, company, role, job_url, applied_date)
        if sent:
            mark_alert_sent(app_id)
            success_count += 1
            print(f"Alert sent: [{app_id}] {role} at {company}")
        else:
            print(f"Failed to send alert for [{app_id}] {role} at {company}")

    print(f"\nDone: {success_count}/{len(pending)} alerts sent.")


# ── Setup helper ───────────────────────────────────────────────────────────────

def get_chat_id():
    """
    Helper to find your chat ID.
    Run this ONCE after creating your bot and sending it a message.
    """
    url      = f"{BASE_URL}/getUpdates"
    response = requests.get(url, timeout=10)
    data     = response.json()

    if not data.get("ok") or not data.get("result"):
        print("No messages found. Send any message to your bot first, then run this.")
        return

    for update in data["result"]:
        msg     = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        name    = msg.get("chat", {}).get("first_name", "")
        text    = msg.get("text", "")
        if chat_id:
            print(f"Chat ID: {chat_id}  |  Name: {name}  |  Message: {text}")
            print(f"\nSet this as your TELEGRAM_CHAT_ID: {chat_id}")
            return

    print("No chat ID found. Make sure you sent a message to your bot first.")


# ── Test ───────────────────────────────────────────────────────────────────────

def test_connection():
    """Send a test message to confirm bot is working."""
    ok = send_message(
        "🤖 *AI Job Agent Connected!*\n\n"
        "Your follow-up alerts are active.\n"
        "I'll notify you when a recruiter hasn't replied in 7 days."
    )
    if ok:
        print("Test message sent successfully!")
    else:
        print("Failed. Check your BOT_TOKEN and CHAT_ID.")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Telegram Bot — Job Follow-up Alert System")
    print("=" * 45)
    print("\n1. test    — Send a test message")
    print("2. chat_id — Find your chat ID")
    print("3. check   — Run daily follow-up check")
    print()

    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        test_connection()
    elif choice == "2":
        get_chat_id()
    elif choice == "3":
        run_daily_check()
    else:
        print("Invalid choice.")