import requests

BOT_TOKEN = "8192445369:AAEpxI3r9imgkfVuV5Y4SDbEmjI9UtosdIs"
CHAT_ID = 248150489  

def send_to_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"❌ Telegram send error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")

def generate_alert_message(row):
    tags = []

    if row.get("HR_Score", 0) >= 0.40:
        tags.append("🔥")
    if row.get("wind_boost", 0) >= 1.5:
        tags.append("💨")
    if row.get("pitch_matchup_score", 0) >= 0.25:
        tags.append("🎯")
    if row.get("bullpen_boost", 0) >= 1.2:
        tags.append("💣")
    if row.get("suppression_tag", False):
        tags.append("🧱")

    tag_str = " ".join(tags)
    name = row.get("batter_name", "Unknown")
    pitcher = row.get("pitcher_name", "Unknown")
    score = row.get("HR_Score", 0)

    return f"{tag_str} *{name}* vs {pitcher} — `Score: {score:.2f}`"

def send_telegram_alerts(df):
    if df.empty:
        print("⚠️ No HR predictions to send.")
        return

    # Buckets
    locks = df[df["HR_Score"] >= 0.40]
    sleepers = df[(df["HR_Score"] >= 0.25) & (df["HR_Score"] < 0.40)]
    risky = df[df["HR_Score"] < 0.25]

    sections = [
        ("🔥 *Lock Picks*", locks),
        ("💤 *Sleepers*", sleepers),
        ("⚠️ *Risky Picks*", risky),
    ]

    for title, group in sections:
        if group.empty:
            continue
        messages = [generate_alert_message(row) for _, row in group.iterrows()]
        full_message = f"{title}:\n" + "\n".join(messages)
        send_to_telegram(full_message)
