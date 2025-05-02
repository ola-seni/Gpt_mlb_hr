import requests
import pandas as pd
from datetime import date

def get_projected_lineups():
    print("📋 Getting projected lineups from MLB Stats API...")
    today = date.today().isoformat()
    projected = []

    # NL ballpark check (DH not always used)
    nl_parks = {
        "CHC", "CIN", "COL", "LAD", "MIA", "MIL",
        "NYM", "PHI", "PIT", "SD", "SF", "STL", "WSH"
    }

    schedule_url = (
        f"https://statsapi.mlb.com/api/v1/schedule?"
        f"sportId=1&hydrate=probablePitcher,team&startDate={today}&endDate={today}"
    )

    try:
        schedule_data = requests.get(schedule_url).json()
        for date_block in schedule_data.get("dates", []):
            for game in date_block.get("games", []):
                teams = game.get("teams", {})
                game_date = game.get("gameDate", today)
                home_team = teams.get("home", {}).get("team", {})
                home_abbr = home_team.get("abbreviation", "")
                is_nl_park = home_abbr in nl_parks

                for side in ["away", "home"]:
                    team_info = teams.get(side, {})
                    team = team_info.get("team", {})
                    team_id = team.get("id")
                    pitcher = team_info.get("probablePitcher", {})
                    pitcher_name = pitcher.get("fullName")
                    pitcher_id = pitcher.get("id")
                    opponent_team = teams.get("home" if side == "away" else "away", {}).get("team", {}).get("name", "Unknown")

                    if not (team_id and pitcher_name and pitcher_id):
                        continue

                    # Fetch team roster
                    roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
                    roster_data = requests.get(roster_url).json()
                    players = roster_data.get("roster", [])

                    # Filter out pitchers and skip DH-only hitters in NL parks
                    batters = [
                        p for p in players
                        if p.get("position", {}).get("abbreviation") not in {"P", "SP", "RP"}
                        and not (is_nl_park and p.get("position", {}).get("abbreviation") == "DH")
                    ]

                    for player in batters[:9]:
                        person = player.get("person", {})
                        batter_name = person.get("fullName")
                        batter_id = person.get("id")
                        if batter_name and batter_id:
                            game_id = f"{batter_name.lower().replace(' ', '_')}__vs__{pitcher_name.lower().replace(' ', '_')}__{today}"
                            projected.append({
                                "batter_name": batter_name,
                                "batter_id": batter_id,
                                "opposing_pitcher": pitcher_name,
                                "pitcher_id": pitcher_id,
                                "pitcher_team": opponent_team,
                                "game_date": today,
                                "game_id": game_id
                            })

        return pd.DataFrame(projected)
    except Exception as e:
        print(f"❌ Failed to fetch projected lineups: {e}")
        return pd.DataFrame()
