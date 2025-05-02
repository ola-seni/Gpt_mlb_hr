import requests
import pandas as pd
import json
import os
import logging
from datetime import date, datetime, timedelta
import time
from utils import generate_game_id

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mlb_api.log")
    ]
)
logger = logging.getLogger("mlb_api")

# Constants
MLB_STATS_API_BASE = "https://statsapi.mlb.com/api"
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_projected_lineups():
    """
    Get projected lineups for today's MLB games from the MLB Stats API.
    Falls back to scraped data from other sources if the API fails.
    
    Returns:
        pandas.DataFrame: DataFrame with lineup information
    """
    logger.info("📋 Getting projected lineups from MLB Stats API...")
    today = date.today().isoformat()
    
    # Cache file path
    cache_path = os.path.join(CACHE_DIR, f"projected_lineups_{today}.json")
    
    # Check if we have a fresh cache (less than 2 hours old)
    if os.path.exists(cache_path):
        cache_time = os.path.getmtime(cache_path)
        now = time.time()
        # If cache is less than 2 hours old, use it
        if now - cache_time < 7200:  # 2 hours in seconds
            logger.info(f"Using cached projected lineup data from {datetime.fromtimestamp(cache_time).strftime('%H:%M:%S')}")
            with open(cache_path, 'r') as f:
                return pd.DataFrame(json.load(f))
    
    try:
        # First try the official MLB Stats API
        projected = fetch_projected_lineups_from_mlb_api()
        
        # If we got valid data, cache it and return
        if not projected.empty:
            lineups_list = projected.to_dict('records')
            with open(cache_path, 'w') as f:
                json.dump(lineups_list, f)
            return projected
    except Exception as e:
        logger.error(f"Error fetching projected lineups from MLB API: {e}", exc_info=True)
    
    # If we get here, the MLB API failed - try fallback sources
    try:
        # Try fallback data source (could be replaced with web scraping)
        projected = get_fallback_projections()
        
        if not projected.empty:
            lineups_list = projected.to_dict('records')
            with open(cache_path, 'w') as f:
                json.dump(lineups_list, f)
            return projected
    except Exception as e:
        logger.error(f"Error fetching fallback projected lineups: {e}", exc_info=True)
    
    # If all attempts failed, return empty DataFrame
    logger.warning("All lineup sources failed, returning empty DataFrame")
    return pd.DataFrame()

def fetch_projected_lineups_from_mlb_api():
    """
    Fetch projected lineups from the MLB Stats API.
    
    Returns:
        pandas.DataFrame: DataFrame with lineup information
    """
    today = date.today().isoformat()
    projected = []
    
    # Get today's schedule to find games and probable pitchers
    schedule_url = (
        f"{MLB_STATS_API_BASE}/v1/schedule"
        f"?sportId=1"
        f"&hydrate=probablePitcher,team,venue"
        f"&startDate={today}"
        f"&endDate={today}"
    )
    
    logger.info(f"Fetching schedule from {schedule_url}")
    response = requests.get(schedule_url, timeout=10)
    
    if response.status_code != 200:
        logger.warning(f"MLB API returned status code {response.status_code}")
        return pd.DataFrame()
    
    schedule_data = response.json()
    
    # Make sure we have dates in the response
    if "dates" not in schedule_data or not schedule_data["dates"]:
        logger.warning("No games found in schedule response")
        return pd.DataFrame()
    
    # Process each game
    for date_block in schedule_data.get("dates", []):
        for game in date_block.get("games", []):
            teams = game.get("teams", {})
            game_date = game.get("gameDate", today)
            venue = game.get("venue", {}).get("name", "Unknown Ballpark")
            
            # Process home and away teams
            home_team = teams.get("home", {}).get("team", {})
            away_team = teams.get("away", {}).get("team", {})
            
            home_id = home_team.get("id")
            home_name = home_team.get("name", "Unknown")
            home_abbr = home_team.get("abbreviation", get_team_code_from_id(home_id))
            
            away_id = away_team.get("id")
            away_name = away_team.get("name", "Unknown")
            away_abbr = away_team.get("abbreviation", get_team_code_from_id(away_id))
            
            logger.info(f"Processing game: {away_name} @ {home_name} at {venue}")
            
            # Get probable pitchers
            home_pitcher = teams.get("home", {}).get("probablePitcher", {})
            away_pitcher = teams.get("away", {}).get("probablePitcher", {})
            
            home_pitcher_name = home_pitcher.get("fullName", "TBD")
            home_pitcher_id = home_pitcher.get("id", 0)
            
            away_pitcher_name = away_pitcher.get("fullName", "TBD")
            away_pitcher_id = away_pitcher.get("id", 0)
            
            # Now get rosters for each team to generate projected lineups
            for side, team_id, team_abbr, opponent_abbr, opponent_pitcher, opponent_pitcher_id in [
                ("home", home_id, home_abbr, away_abbr, away_pitcher_name, away_pitcher_id),
                ("away", away_id, away_abbr, home_abbr, home_pitcher_name, home_pitcher_id)
            ]:
                try:
                    # Get roster for this team
                    roster_url = f"{MLB_STATS_API_BASE}/v1/teams/{team_id}/roster/active"
                    roster_response = requests.get(roster_url, timeout=10)
                    
                    if roster_response.status_code != 200:
                        logger.warning(f"Failed to get roster for team {team_id}, status: {roster_response.status_code}")
                        continue
                    
                    roster_data = roster_response.json()
                    
                    # Filter for position players
                    position_players = [
                        player for player in roster_data.get("roster", [])
                        if player.get("position", {}).get("abbreviation") not in ["P", "SP", "RP"]
                    ]
                    
                    # Take the first 9 players as a simple projection
                    # In a real implementation, you would use machine learning or historical data
                    # to predict the actual lineup based on pitcher handedness, etc.
                    for player in position_players[:9]:
                        person = player.get("person", {})
                        batter_name = person.get("fullName")
                        batter_id = person.get("id")
                        
                        if batter_name and batter_id:
                            game_id = generate_game_id(batter_name, opponent_pitcher, today)
                            
                            projected.append({
                                "batter_name": batter_name,
                                "batter_id": batter_id,
                                "opposing_pitcher": opponent_pitcher,
                                "pitcher_id": opponent_pitcher_id,
                                "pitcher_team": opponent_abbr,
                                "game_date": today,
                                "game_id": game_id,
                                "ballpark": venue,
                                "home_team": home_abbr
                            })
                except Exception as e:
                    logger.error(f"Error processing roster for team {team_id}: {e}")
    
    if not projected:
        logger.warning("No projected lineups found from MLB API")
        return pd.DataFrame()
    
    return pd.DataFrame(projected)

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

def get_ballpark_name(team_code):
    """Get the ballpark name for a given team code"""
    ballpark_mapping = {
        "ARI": "Chase Field",
        "ATL": "Truist Park",
        "BAL": "Oriole Park at Camden Yards",
        "BOS": "Fenway Park",
        "CHC": "Wrigley Field",
        "CWS": "Guaranteed Rate Field",
        "CIN": "Great American Ball Park",
        "CLE": "Progressive Field",
        "COL": "Coors Field",
        "DET": "Comerica Park",
        "HOU": "Minute Maid Park",
        "KC": "Kauffman Stadium",
        "LAA": "Angel Stadium",
        "LAD": "Dodger Stadium",
        "MIA": "LoanDepot Park",
        "MIL": "American Family Field",
        "MIN": "Target Field",
        "NYM": "Citi Field",
        "NYY": "Yankee Stadium",
        "OAK": "Oakland Coliseum",
        "PHI": "Citizens Bank Park",
        "PIT": "PNC Park",
        "SD": "Petco Park",
        "SF": "Oracle Park",
        "SEA": "T-Mobile Park",
        "STL": "Busch Stadium",
        "TB": "Tropicana Field",
        "TEX": "Globe Life Field",
        "TOR": "Rogers Centre",
        "WSH": "Nationals Park"
    }
    return ballpark_mapping.get(team_code, f"{team_code} Ballpark")

def get_fallback_projections():
    """
    Return fallback projected lineups when the MLB API fails.
    This function could be enhanced with web scraping from other sources.
    
    Returns:
        pandas.DataFrame: DataFrame with projected lineup information
    """
    today = date.today().isoformat()
    
    # You could implement web scraping from ESPN, CBS Sports, etc. here
    # For now, we'll use a hardcoded list of likely games and matchups
    # Based on today's date

    # Sample games for demonstration - in a real implementation,
    # you would scrape this data from reliable sources
    todays_games = [
        # Yankees @ Orioles
        {
            "away": "NYY",
            "home": "BAL",
            "away_pitcher": "Gerrit Cole",
            "away_pitcher_id": 543037,
            "home_pitcher": "Corbin Burnes",
            "home_pitcher_id": 669203,
            "ballpark": "Oriole Park at Camden Yards"
        },
        # Mets @ Cardinals
        {
            "away": "NYM",
            "home": "STL",
            "away_pitcher": "Luis Severino",
            "away_pitcher_id": 622663,
            "home_pitcher": "Miles Mikolas",
            "home_pitcher_id": 571945,
            "ballpark": "Busch Stadium"
        },
        # Dodgers @ Giants
        {
            "away": "LAD",
            "home": "SF",
            "away_pitcher": "Tyler Glasnow",
            "away_pitcher_id": 607192,
            "home_pitcher": "Logan Webb",
            "home_pitcher_id": 657277,
            "ballpark": "Oracle Park"
        },
        # Braves @ Phillies
        {
            "away": "ATL",
            "home": "PHI",
            "away_pitcher": "Spencer Strider",
            "away_pitcher_id": 675911,
            "home_pitcher": "Zack Wheeler",
            "home_pitcher_id": 554430,
            "ballpark": "Citizens Bank Park"
        }
    ]
    
    # Players likely to be in lineups by team
    team_players = {
        "NYY": [
            {"name": "Aaron Judge", "id": 592450},
            {"name": "Juan Soto", "id": 665742},
            {"name": "Giancarlo Stanton", "id": 519317},
            {"name": "Anthony Rizzo", "id": 519203},
            {"name": "Gleyber Torres", "id": 650402},
            {"name": "Anthony Volpe", "id": 683011},
            {"name": "Alex Verdugo", "id": 657077},
            {"name": "Jose Trevino", "id": 644338},
            {"name": "Jazz Chisholm Jr.", "id": 665862}
        ],
        "BAL": [
            {"name": "Adley Rutschman", "id": 668939},
            {"name": "Gunnar Henderson", "id": 683002},
            {"name": "Ryan Mountcastle", "id": 663624},
            {"name": "Anthony Santander", "id": 623993},
            {"name": "Austin Hays", "id": 669720},
            {"name": "Cedric Mullins", "id": 656775},
            {"name": "Jordan Westburg", "id": 688171},
            {"name": "Ramon Urias", "id": 602104},
            {"name": "James McCann", "id": 543510}
        ],
        "NYM": [
            {"name": "Francisco Lindor", "id": 596019},
            {"name": "Pete Alonso", "id": 624413},
            {"name": "Starling Marte", "id": 516782},
            {"name": "Brandon Nimmo", "id": 607043},
            {"name": "J.D. Martinez", "id": 502110},
            {"name": "Jeff McNeil", "id": 643446},
            {"name": "Francisco Alvarez", "id": 682626},
            {"name": "Brett Baty", "id": 683146},
            {"name": "Harrison Bader", "id": 664056}
        ],
        "STL": [
            {"name": "Nolan Arenado", "id": 571448},
            {"name": "Paul Goldschmidt", "id": 502671},
            {"name": "Willson Contreras", "id": 575929},
            {"name": "Jordan Walker", "id": 693330},
            {"name": "Brendan Donovan", "id": 680977},
            {"name": "Nolan Gorman", "id": 669357},
            {"name": "Alec Burleson", "id": 687998},
            {"name": "Tommy Edman", "id": 669242},
            {"name": "Lars Nootbaar", "id": 663457}
        ],
        "LAD": [
            {"name": "Mookie Betts", "id": 605141},
            {"name": "Shohei Ohtani", "id": 660271},
            {"name": "Freddie Freeman", "id": 518692},
            {"name": "Will Smith", "id": 669257},
            {"name": "Max Muncy", "id": 571970},
            {"name": "Teoscar Hernandez", "id": 606192},
            {"name": "Jason Heyward", "id": 518792},
            {"name": "Gavin Lux", "id": 666158},
            {"name": "Enrique Hernandez", "id": 571771}
        ],
        "SF": [
            {"name": "Jung Hoo Lee", "id": 700182},
            {"name": "Matt Chapman", "id": 656305},
            {"name": "Michael Conforto", "id": 624424},
            {"name": "Jorge Soler", "id": 624585},
            {"name": "Thairo Estrada", "id": 642731},
            {"name": "Heliot Ramos", "id": 671218},
            {"name": "LaMonte Wade Jr.", "id": 664774},
            {"name": "Patrick Bailey", "id": 672275},
            {"name": "Nick Ahmed", "id": 605113}
        ],
        "ATL": [
            {"name": "Ronald Acuna Jr.", "id": 660670},
            {"name": "Ozzie Albies", "id": 645277},
            {"name": "Austin Riley", "id": 663586},
            {"name": "Matt Olson", "id": 621566},
            {"name": "Marcell Ozuna", "id": 542303},
            {"name": "Michael Harris II", "id": 671739},
            {"name": "Sean Murphy", "id": 669221},
            {"name": "Orlando Arcia", "id": 606115},
            {"name": "Jarred Kelenic", "id": 672284}
        ],
        "PHI": [
            {"name": "Trea Turner", "id": 607208},
            {"name": "Kyle Schwarber", "id": 656941},
            {"name": "Bryce Harper", "id": 547180},
            {"name": "J.T. Realmuto", "id": 592663},
            {"name": "Nick Castellanos", "id": 592206},
            {"name": "Alec Bohm", "id": 664761},
            {"name": "Bryson Stott", "id": 681082},
            {"name": "Brandon Marsh", "id": 669016},
            {"name": "Whit Merrifield", "id": 593160}
        ]
    }
    
    # Build projected lineups
    projected = []
    
    for game in todays_games:
        away_team = game["away"]
        home_team = game["home"]
        ballpark = game["ballpark"]
        
        # Generate away team lineup
        for player in team_players.get(away_team, []):
            projected.append({
                "batter_name": player["name"],
                "batter_id": player["id"],
                "opposing_pitcher": game["home_pitcher"],
                "pitcher_id": game["home_pitcher_id"],
                "pitcher_team": home_team,
                "game_date": today,
                "game_id": generate_game_id(player["name"], game["home_pitcher"], today),
                "ballpark": ballpark,
                "home_team": home_team
            })
        
        # Generate home team lineup
        for player in team_players.get(home_team, []):
            projected.append({
                "batter_name": player["name"],
                "batter_id": player["id"],
                "opposing_pitcher": game["away_pitcher"],
                "pitcher_id": game["away_pitcher_id"],
                "pitcher_team": away_team,
                "game_date": today,
                "game_id": generate_game_id(player["name"], game["away_pitcher"], today),
                "ballpark": ballpark,
                "home_team": home_team
            })
    
    logger.info(f"Generated {len(projected)} fallback projected lineups")
    return pd.DataFrame(projected)

# For testing
if __name__ == "__main__":
    lineups = get_projected_lineups()
    print(f"Found {len(lineups)} projected lineups")
    if not lineups.empty:
        print(lineups.head())
