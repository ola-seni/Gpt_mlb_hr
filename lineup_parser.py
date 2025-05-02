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
                "pitcher_team": "NYY",  # Make sure team codes are uppercase and consistent
                "game_date": today,
                "game_id": generate_game_id("Aaron Judge", "Clarke Schmidt", today),
                "ballpark": "Yankee Stadium",
                "home_team": "NYY"  # Add home team explicitly
            },
            {
                "batter_name": "Juan Soto",
                "batter_id": 665742,
                "opposing_pitcher": "Max Scherzer",
                "pitcher_id": 453286,
                "pitcher_team": "TEX",
                "game_date": today,
                "game_id": generate_game_id("Juan Soto", "Max Scherzer", today),
                "ballpark": "Arlington Stadium",
                "home_team": "TEX"
            },
            {
                "batter_name": "Shohei Ohtani",
                "batter_id": 660271,
                "opposing_pitcher": "Cal Quantrill",
                "pitcher_id": 663371,
                "pitcher_team": "COL",
                "game_date": today,
                "game_id": generate_game_id("Shohei Ohtani", "Cal Quantrill", today),
                "ballpark": "Coors Field",
                "home_team": "COL"
            },
            {
                "batter_name": "Kyle Schwarber",
                "batter_id": 656941,
                "opposing_pitcher": "Dakota Hudson",
                "pitcher_id": 605308,
                "pitcher_team": "STL",
                "game_date": today,
                "game_id": generate_game_id("Kyle Schwarber", "Dakota Hudson", today),
                "ballpark": "Busch Stadium",
                "home_team": "STL"
            },
            {
                "batter_name": "Vladimir Guerrero Jr.",
                "batter_id": 665489,
                "opposing_pitcher": "Luke Weaver",
                "pitcher_id": 642152,
                "pitcher_team": "MIL",
                "game_date": today,
                "game_id": generate_game_id("Vladimir Guerrero Jr.", "Luke Weaver", today),
                "ballpark": "American Family Field",
                "home_team": "MIL"
            },
            {
                "batter_name": "Pete Alonso",
                "batter_id": 666163,
                "opposing_pitcher": "Kyle Freeland",
                "pitcher_id": 607536,
                "pitcher_team": "COL",
                "game_date": today,
                "game_id": generate_game_id("Pete Alonso", "Kyle Freeland", today),
                "ballpark": "Coors Field",
                "home_team": "COL"
            },
            {
                "batter_name": "Bryce Harper",
                "batter_id": 547180,
                "opposing_pitcher": "Trevor Williams",
                "pitcher_id": 592866,
                "pitcher_team": "WSH",
                "game_date": today,
                "game_id": generate_game_id("Bryce Harper", "Trevor Williams", today),
                "ballpark": "Nationals Park",
                "home_team": "WSH"
            }
        ])

    try:
        print("📋 Getting lineups from MLB Stats API...")
        today = date.today().isoformat()
        schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=lineups,probablePitcher,venue,team"

        schedule = requests.get(schedule_url).json()
        games = schedule.get("dates", [])
        
        if not games:
            print("⚠️ No games found for today via MLB API.")
            return pd.DataFrame()
            
        games = games[0].get("games", [])

        all_lineups = []
        for game in games:
            game_id = game.get("gamePk")
            teams = game.get("teams", {})
            venue = game.get("venue", {}).get("name", "Unknown Ballpark")
            
            home_team = teams.get("home", {}).get("team", {})
            away_team = teams.get("away", {}).get("team", {})
            
            home_name = home_team.get("name", "Unknown")
            away_name = away_team.get("name", "Unknown")
            
            # Get team codes
            home_code = home_team.get("abbreviation", "")
            if not home_code:
                # Try to get from team ID using known mappings
                home_id = home_team.get("id", 0)
                home_code = get_team_code_from_id(home_id)
                
            away_code = away_team.get("abbreviation", "")
            if not away_code:
                away_id = away_team.get("id", 0)
                away_code = get_team_code_from_id(away_id)

            for side in ["home", "away"]:
                roster = teams.get(side, {})
                lineup = roster.get("lineup", {}).get("expected", {}).get("lineup", [])
                
                pitcher_info = roster.get("probablePitcher", {})
                pitcher = pitcher_info.get("fullName", "Unknown Pitcher")
                pitcher_id = pitcher_info.get("id", 999999)
                
                # Determine opponent team code
                opponent_code = away_code if side == "home" else home_code
                venue_name = venue
                home_venue = venue if side == "away" else ""  # Only set for away team batters

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
                        "pitcher_team": opponent_code,
                        "game_date": game_date,
                        "game_id": matchup_id,
                        "ballpark": venue_name,
                        "home_team": home_code if side == "away" else away_code
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

def get_team_code_from_id(team_id):
    """Map MLB team IDs to team codes when abbreviation is not available"""
    team_mapping = {
        108: "LAA",  # Angels
        109: "ARI",  # Diamondbacks
        110: "BAL",  # Orioles
        111: "BOS",  # Red Sox
        112: "CHC",  # Cubs
        113: "CIN",  # Reds
        114: "CLE",  # Guardians
        115: "COL",  # Rockies
        116: "DET",  # Tigers
        117: "HOU",  # Astros
        118: "KC",   # Royals
        119: "LAD",  # Dodgers
        120: "WSH",  # Nationals
        121: "NYM",  # Mets
        133: "OAK",  # Athletics
        134: "PIT",  # Pirates
        135: "SD",   # Padres
        136: "SEA",  # Mariners
        137: "SF",   # Giants
        138: "STL",  # Cardinals
        139: "TB",   # Rays
        140: "TEX",  # Rangers
        141: "TOR",  # Blue Jays
        142: "MIN",  # Twins
        143: "PHI",  # Phillies
        144: "ATL",  # Braves
        145: "CWS",  # White Sox
        146: "MIA",  # Marlins
        158: "MIL",  # Brewers
        147: "NYY",  # Yankees
    }
    return team_mapping.get(team_id, "UNK")
