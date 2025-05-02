import requests
import pandas as pd
from datetime import date
from utils import generate_game_id

def get_confirmed_lineups(force_test=False):
    if force_test:
        print("🧪 Test mode enabled: using fallback lineups")
        today = date.today().isoformat()
        return pd.DataFrame([
            {
                "batter_name": "Aaron Judge",
                "batter_id": 592450,
                "opposing_pitcher": "Clarke Schmidt",
                "pitcher_id": 688676,
                "pitcher_team": "NYY",
                "game_date": today,
                "game_id": generate_game_id("Aaron Judge", "Clarke Schmidt", today)
            },
            {
                "batter_name": "Juan Soto",
                "batter_id": 665742,
                "opposing_pitcher": "Max Scherzer",
                "pitcher_id": 453286,
                "pitcher_team": "TEX",
                "game_date": today,
                "game_id": generate_game_id("Juan Soto", "Max Scherzer", today)
            }
        ])

    try:
        print("📋 Getting lineups from MLB Stats API...")
        today = date.today().isoformat()
        schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=lineups,probablePitcher"

        schedule = requests.get(schedule_url).json()
        games = schedule.get("dates", [])[0].get("games", [])

        all_lineups = []
        for game in games:
            game_id = game.get("gamePk")
            teams = game.get("teams", {})
            home = teams.get("home", {}).get("team", {}).get("name")
            away = teams.get("away", {}).get("team", {}).get("name")

            for side in ["home", "away"]:
                roster = teams.get(side, {})
                lineup = roster.get("lineup", {}).get("expected", {}).get("lineup", [])
                pitcher = roster.get("probablePitcher", {}).get("fullName", "Unknown Pitcher")
                pitcher_id = roster.get("probablePitcher", {}).get("id", 999999)

                for player in lineup:
                    if "fullName" not in player or "id" not in player:
                        continue
                    batter_name = player["fullName"]
                    batter_id = player["id"]
                    game_date = today
                    matchup_id = generate_game_id(batter_name, pitcher, game_date)

                    all_lineups.append({
                        "batter_name": batter_name,
                        "batter_id": batter_id,
                        "opposing_pitcher": pitcher,
                        "pitcher_id": pitcher_id,
                        "pitcher_team": home if side == "away" else away,
                        "game_date": game_date,
                        "game_id": matchup_id
                    })

        df = pd.DataFrame(all_lineups)
        if df.empty:
            print("⚠️ No confirmed lineups found via MLB API.")
        else:
            print(f"✅ Loaded {len(df)} confirmed hitters from MLB Stats API.")
        return df

    except Exception as e:
        print(f"❌ Failed to fetch lineups from MLB Stats API: {e}")
        return pd.DataFrame()