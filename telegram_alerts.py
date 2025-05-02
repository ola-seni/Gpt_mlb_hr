
from dotenv import load_dotenv
from pathlib import Path
import os
import requests
import re

# ⬇️ Force load .env relative to script location
dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("❌ Missing BOT_TOKEN or CHAT_ID in your .env file. Please fix and reload with: source .env")
    exit(1)

def escape_markdown(text):
    """Escape Telegram MarkdownV2 special characters."""
    escape_chars = r'\_*[]()~`>#+=|{}.!-'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def send_telegram_alerts(predictions):
    if predictions.empty or "HR_Score" not in predictions.columns:
        print("⚠️ No HR predictions to send.")
        return

    def format_player(row):
        name = escape_markdown(row.get("batter_name", "Unknown"))
        pitcher = escape_markdown(row.get("opposing_pitcher", "Unknown"))
        park = escape_markdown(row.get("ballpark", ""))
        hr_score = f"`{row['HR_Score']:.3f}`"
        matchup_score = f"`{row.get('pitch_matchup_score', 0):.3f}`"
        wind_boost = f"`{row.get('wind_boost', 0):.2f}`"
        park_boost = f"`{row.get('park_factor', 0):.2f}`"
        note = row.get("tag", "")

        message = (
            f"*{name}* vs *{pitcher}*\n"
            f"📍 Ballpark: {park} 🏟️\n"
            f"🔥 HR Score: {hr_score}\n"
            f"🎯 Pitch Matchup: {matchup_score}\n"
            f"🌬️ Wind Boost: {wind_boost}\n"
            f"🏞️ Park Factor: {park_boost}\n"
        )
        if note:
            message += f"📝 _{escape_markdown(note)}_\n"
        return message.strip()

    groups = {
        "Locks 🔒": predictions[predictions["tag"] == "Lock"],
        "Sleepers 🌙": predictions[predictions["tag"] == "Sleeper"],
        "Risky ⚠️": predictions[predictions["tag"] == "Risky"]
    }

    any_sent = False
    for group_name, group_df in groups.items():
        if group_df.empty:
            continue
        sorted_df = group_df.sort_values("HR_Score", ascending=False)
        msg = f"*{escape_markdown(group_name)}*\n\n"
        msg += "\n\n".join(format_player(row) for _, row in sorted_df.iterrows())
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "MarkdownV2"
        }
        try:
            res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
            res.raise_for_status()
            any_sent = True
        except Exception as e:
            print(f"❌ Telegram send error for {group_name}: {e}")

    if not any_sent:
        fallback_msg = "*No strong home run picks today.* Stay tuned for tomorrow's predictions. ⚾️"
        payload = {
            "chat_id": CHAT_ID,
            "text": fallback_msg,
            "parse_mode": "MarkdownV2"
        }
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
        except Exception as e:
            print(f"❌ Telegram fallback error: {e}")
