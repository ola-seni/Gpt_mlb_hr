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
    
    # Get top 5 predictions sorted by matchup_score if available, otherwise HR_Score
    sort_column = "matchup_score" if "matchup_score" in predictions.columns else "HR_Score"
    top_predictions = predictions.sort_values(sort_column, ascending=False).head(5)
    
    # Create a header with current date
    msg = f"⚾ *MLB Home Run Predictions*\n*{format_date()}*\n\n"
    
    # Add top picks
    for idx, (_, row) in enumerate(top_predictions.iterrows(), 1):
        name = row.get("batter_name", "Unknown")
        pitcher = row.get("pitcher_display_name", row.get("opposing_pitcher", "Unknown Pitcher"))
        hr_score = row.get("matchup_score", row.get("HR_Score", 0))
        ballpark = row.get("ballpark", "")
        tag = row.get("tag", "")
        
        # Format nicely
        msg += f"*{idx}. {name}* vs {pitcher}\n"
        msg += f"   📊 Score: {hr_score:.3f} | {tag}\n"
        if ballpark:
            msg += f"   🏟️ {ballpark}\n"
        msg += "\n"
    
    # Add footer
    msg += "\n_Powered by MLB Statcast & Advanced Analytics_"
    
    # Use normal Markdown for simpler formatting
    simple_payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
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

    # Now send detailed category breakdowns
    try:
        # Process each prediction category
        groups = {
            "Locks 🔒": predictions[predictions["tag"] == "Lock 🔒"],
            "Sleepers 🌙": predictions[predictions["tag"] == "Sleeper 🌙"],
            "Risky ⚠️": predictions[predictions["tag"] == "Risky ⚠️"]
        }

        # For empty categories, take some from other categories
        if groups["Sleepers 🌙"].empty and not groups["Locks 🔒"].empty:
            print("Finding alternative Sleeper picks...")
            # Take bottom half of Locks as Sleepers
            locks = groups["Locks 🔒"].sort_values(sort_column, ascending=False)
            half_idx = max(1, len(locks) // 2)
            groups["Sleepers 🌙"] = locks.iloc[half_idx:].copy()
            groups["Sleepers 🌙"]["tag"] = "Sleeper 🌙"
            # Keep only top half as Locks
            groups["Locks 🔒"] = locks.iloc[:half_idx]

        if groups["Risky ⚠️"].empty and not groups["Sleepers 🌙"].empty:
            print("Finding alternative Risky picks...")
            # Take bottom half of Sleepers as Risky
            sleepers = groups["Sleepers 🌙"].sort_values(sort_column, ascending=False)
            half_idx = max(1, len(sleepers) // 2)
            groups["Risky ⚠️"] = sleepers.iloc[half_idx:].copy()
            groups["Risky ⚠️"]["tag"] = "Risky ⚠️"
            # Keep only top half as Sleepers
            groups["Sleepers 🌙"] = sleepers.iloc[:half_idx]

        # Ensure exclusivity between categories
        processed_players = set()

        for group_name, group_df in groups.items():
            if not group_df.empty:
                # Remove players already processed in previous categories
                group_df = group_df[~group_df["batter_name"].isin(processed_players)]
                groups[group_name] = group_df
                
                # Add these players to processed set so they don't appear again
                processed_players.update(group_df["batter_name"].tolist())
                
                # Sort each group by the appropriate score column
                sorted_df = group_df.sort_values(sort_column, ascending=False)
                groups[group_name] = sorted_df

        # Add right after you define the groups dictionary
        for group_name, group_df in groups.items():
            if group_df.empty:
                print(f"⚠️ No predictions in {group_name} category")
                # If a category is empty, get the top predictions that would normally
                # be just below the threshold and add them to this category
                if group_name == "Sleepers 🌙":
                    # Get predictions just below Lock threshold
                    almost_sleepers = predictions.sort_values(sort_column, ascending=False)
                    almost_sleepers = almost_sleepers[~almost_sleepers.index.isin(groups["Locks 🔒"].index)]
                    groups[group_name] = almost_sleepers.head(3)
                elif group_name == "Risky ⚠️":
                    # Get predictions just below Sleeper threshold
                    almost_risky = predictions.sort_values(sort_column, ascending=False)
                    almost_risky = almost_risky[~almost_risky.index.isin(groups["Locks 🔒"].index) & 
                                                ~almost_risky.index.isin(groups["Sleepers 🌙"].index)]
                    groups[group_name] = almost_risky.head(3)
            
            # Limit to top 5 players per group
            if len(sorted_df) > 5:
                print(f"⚠️ Limiting {group_name} to top 5 of {len(sorted_df)} predictions")
                sorted_df = sorted_df.head(5)
            
            # Create detailed message
            detailed_msg = f"*⚾ MLB Home Run Predictions: {group_name}*\n\n"
            
            for _, row in sorted_df.iterrows():
                name = row.get("batter_name", "Unknown")
                pitcher = row.get("pitcher_display_name", row.get("opposing_pitcher", "Unknown Pitcher"))
                if pd.isna(pitcher):
                    pitcher = "Unknown Pitcher"
                
                # Get score values
                hr_score = row.get("HR_Score", 0)
                ballpark = row.get("ballpark", "Unknown Ballpark")
                park_factor = row.get("park_factor", 1.0)
                wind_boost = row.get("wind_boost", 0)
                
                # Create a more detailed and better formatted message
                detailed_msg += f"*{name}* vs *{pitcher}*\n"
                detailed_msg += f"📍 Ballpark: {ballpark} 🏟️ ({park_factor:.2f})\n"
                detailed_msg += f"🔥 HR Score: {hr_score:.3f}\n"
                detailed_msg += f"🌬️ Wind Effect: {wind_boost:.2f}\n\n"
            
            # Send with regular Markdown
            category_payload = {
                "chat_id": CHAT_ID,
                "text": detailed_msg,
                "parse_mode": "Markdown"
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
                
    except Exception as e:
        print(f"❌ Error preparing category messages: {e}")
