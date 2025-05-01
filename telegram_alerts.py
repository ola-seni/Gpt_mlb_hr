import requests

BOT_TOKEN = "8192445369:AAEpxI3r9imgkfVuV5Y4SDbEmjI9UtosdIs"
CHAT_ID = 248150489  

def send_telegram_alerts(df):
    print("📨 Sending Telegram alerts...")

    if df.empty:
        message = "⚠️ No predictions generated today."
    else:
        top = df.sort_values("HR_Score", ascending=False).head(10)
        message = "🔥 *Top HR Predictions Today:*\n"
        for _, row in top.iterrows():
            message += f"• *{row['batter_name']}* vs {row['pitcher_name']} → `{row['HR_Score']:.2f}` | {row['Label']}\n"

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    )
