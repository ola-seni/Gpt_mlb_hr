from dotenv import load_dotenv
from pathlib import Path
import os
import requests
import re
from datetime import datetime

# ⬇️ Force load .env relative to script location
dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("❌ Missing BOT_TOKEN or CHAT_ID in your .env file. Please fix and reload with: source .env")

def escape_markdown(text):
    """Escape Telegram MarkdownV2 special characters more thoroughly."""
    if not text:
        return ""
    text = str(text)
    # Escape these characters: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'_*[]()~`>#+=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text

def format_date():
    """Format today's date in a nice way."""
    return datetime.now().strftime("%A, %B %d, %Y")

def send_telegram_alerts(predictions):
    if predictions.empty or "HR_Score" not in predictions.columns:
        print("⚠️ No HR predictions to send.")
        return

    # First send a simple formatted message with top picks
    print("🔔 Sending top picks message...")
    
    # Get top 5 predictions sorted by HR_Score
    top_predictions = predictions.sort_values("HR_Score", ascending=False).head(5)
    
    # Create a simple message with basic formatting
    msg = f"MLB Home Run Predictions for {format_date()}:\n\n"
    
    for idx, (_, row) in enumerate(top_predictions.iterrows(), 1):
        name = row.get("batter_name", "Unknown")
        pitcher = row.get("opposing_pitcher", "Unknown Pitcher")
        hr_score = row.get("HR_Score", 0)
        ballpark = row.get("ballpark", "")
        park_info = f" at {ballpark}" if ballpark else ""
        
        msg += f"{idx}. {name} vs {pitcher}{park_info}: {hr_score:.3f}\n"
    
    simple_payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"  # Regular Markdown is safer
    }
    
    try:
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=simple_payload)
        print(f"Top picks message response: {res.status_code}")
        if res.status_code != 200:
            print(f"Top picks message failed: {res.text}")
        else:
            print("✅ Top picks message sent successfully")
    except Exception as e:
        print(f"❌ Telegram top picks error: {e}")

    # Now try to send detailed breakdown by categories
    groups = {
        "Locks 🔒": predictions[predictions["tag"] == "Lock 🔒"],
        "Sleepers 🌙": predictions[predictions["tag"] == "Sleeper 🌙"],
        "Risky ⚠️": predictions[predictions["tag"] == "Risky ⚠️"]
    }

    # Process each category separately with safer formatting
    for group_name, group_df in groups.items():
        if group_df.empty:
            print(f"⚠️ No predictions in {group_name} category")
            continue
        
        sorted_df = group_df.sort_values("HR_Score", ascending=False)
        
        # Limit to top 5 players per group
        if len(sorted_df) > 5:
            print(f"⚠️ Limiting {group_name} to top 5 of {len(sorted_df)} predictions")
            sorted_df = sorted_df.head(5)
        
        # Create a detailed message for this category
        category_msg = f"MLB HR Predictions: {group_name}\n\n"
        
        for _, row in sorted_df.iterrows():
            name = row.get("batter_name", "Unknown")
            pitcher = row.get("opposing_pitcher", "Unknown")
            team = row.get("pitcher_team", "")
            team_info = f" ({team})" if team else ""
            
            hr_score = row.get("HR_Score", 0)
            park = row.get("ballpark", "")
            park_factor = row.get("park_factor", 1.0)
            wind_boost = row.get("wind_boost", 0)
            
            category_msg += (
                f"• {name} vs {pitcher}{team_info}\n"
                f"  HR Score: {hr_score:.3f} | Park: {park} ({park_factor:.2f})\n"
                f"  Wind Effect: {wind_boost:.2f}\n\n"
            )
        
        # Send with regular Markdown formatting
        category_payload = {
            "chat_id": CHAT_ID,
            "text": category_msg,
            "parse_mode": "Markdown"  # Regular Markdown is safer
        }
        
        try:
            print(f"🔔 Sending {group_name} category...")
            res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=category_payload)
            print(f"{group_name} response: {res.status_code}")
            if res.status_code != 200:
                print(f"{group_name} message failed: {res.text}")
            else:
                print(f"✅ {group_name} message sent successfully")
        except Exception as e:
            print(f"❌ Telegram {group_name} error: {e}")
