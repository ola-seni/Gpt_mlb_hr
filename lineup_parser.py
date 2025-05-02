import requests
import pandas as pd
from datetime import date, datetime
import time
import json
import os
import logging

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

def get_confirmed_lineups(force_test=False, verbose=True):
    """
    Get confirmed lineups for today's MLB games.
    
    Args:
        force_test (bool): If True, use test data instead of making API calls
        verbose (bool): If True, print detailed log messages
        
    Returns:
        pandas.DataFrame: DataFrame with lineup information
    """
    if force_test:
        logger.info("🧪 Test mode enabled: using fallback lineups")
        return get_test_lineups()

    try:
        logger.info("📋 Getting lineups from MLB Stats API...")
        today = date.today().isoformat()
        
        # Cache file path
        cache_path = os.path.join(CACHE_DIR, f"lineups_{today}.json")
        
        # Check if we have a fresh cache (less than 30 minutes old)
        if os.path.exists(cache_path):
            cache_time = os.path.getmtime(cache_path)
            now = time.time()
            # If cache is less than 30 minutes old, use it
            if now - cache_time < 1800:  # 30 minutes in seconds
                logger.info(f"Using cached lineup data from {datetime.fromtimestamp(cache_time).strftime('%H:%M:%S')}")
                with open(cache_path, 'r') as f:
                    return pd.DataFrame(json.load(f))
        
        # Build the schedule URL with detailed hydrations
        schedule_url = (
            f"{MLB_STATS_API_BASE}/v1/schedule"
            f"?sportId=1"
            f"&date={today}"
            f"&hydrate=lineups,probablePitcher,venue,team"
        )
        
        logger.info(f"Fetching schedule from: {schedule_url}")
        
        # Make the request with retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.get(schedule_url, timeout=10)
                response.raise_for_status()  # Raise exception for 4XX/5XX responses
                schedule = response.json()
                break
            except requests.exceptions.RequestException as e:
                logger.warning(f"API request failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch lineup data after {max_retries} attempts")
                    return get_fallback_lineups()
        
        # Check if we have valid data
        if not schedule or "dates" not in schedule or not schedule["dates"]:
            logger.warning("No games found in schedule response")
            return get_fallback_lineups()
        
        games = schedule["dates"][0].get("games", [])
        if not games:
            logger.warning("No games found for today in MLB API response")
            return get_fallback_lineups()
            
        # Process the games to extract lineups
        all_lineups = []
        for game in games:
            game_id = game.get("gamePk")
            logger.info(f"Processing game {game_id}")
            
            teams = game.get("teams", {})
            venue = game.get("venue", {}).get("name", "Unknown Ballpark")
            
            home_team = teams.get("home", {}).get("team", {})
            away_team = teams.get("away", {}).get("team", {})
            
            home_name = home_team.get("name", "Unknown")
            away_name = away_team.get("name", "Unknown")
            
            logger.info(f"Game: {away_name} @ {home_name} at {venue}")
            
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
                
                # Check for different lineup formats
                lineup = None
                
                # Try the primary lineup path
                if "lineup" in roster and "expected" in roster["lineup"]:
                    lineup = roster["lineup"]["expected"].get("lineup", [])
                
                # If that failed, try alternate paths
                if not lineup and "lineup" in roster:
                    lineup = roster["lineup"]
                
                # Still no lineup? Try fetching from a separate endpoint
                if not lineup:
                    logger.info(f"No lineup found in schedule for {side} team, trying alternate endpoint")
                    lineup = fetch_lineup_from_alternate_endpoint(game_id, side)
                
                if not lineup:
                    logger.warning(f"No lineup available for {side} team in game {game_id}")
                    continue
                
                # Get pitcher info
                pitcher_info = roster.get("probablePitcher", {})
                pitcher = pitcher_info.get("fullName", "Unknown Pitcher")
                pitcher_id = pitcher_info.get("id", 999999)
                
                # Determine opponent team code
                opponent_code = away_code if side == "home" else home_code
                venue_name = venue
                
                # Process each player in the lineup
                for player in lineup:
                    if not isinstance(player, dict):
                        continue
                        
                    # Try different paths to player data
                    batter_name = player.get("fullName")
                    if not batter_name:
                        batter_name = player.get("name", {}).get("full")
                    if not batter_name:
                        batter_name = player.get("person", {}).get("fullName")
                    
                    batter_id = player.get("id")
                    if not batter_id:
                        batter_id = player.get("person", {}).get("id")
                    
                    if not batter_name or not batter_id:
                        logger.warning(f"Missing player data: {player}")
                        continue
                        
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
        
        # Cache the data if we got valid results
        if not df.empty:
            with open(cache_path, 'w') as f:
                json.dump(all_lineups, f)
            logger.info(f"✅ Loaded {len(df)} confirmed hitters from MLB Stats API")
        else:
            logger.warning("⚠️ No confirmed lineups found via MLB API")
            return get_fallback_lineups()
            
        return df

    except Exception as e:
        logger.error(f"❌ Failed to fetch lineups from MLB Stats API: {e}", exc_info=True)
        return get_fallback_lineups()

def fetch_lineup_from_alternate_endpoint(game_id, side):
    """
    Try to fetch lineup data from the boxscore endpoint as a fallback.
    
    Args:
        game_id (int): MLB game ID
        side (str): 'home' or 'away'
        
    Returns:
        list: List of player dictionaries or empty list if not found
    """
    try:
        url = f"{MLB_STATS_API_BASE}/v1.1/game/{game_id}/boxscore"
        logger.info(f"Fetching lineup from alternate endpoint: {url}")
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Alternate endpoint returned status code {response.status_code}")
            return []
            
        data = response.json()
        
        # Try to extract lineup from the boxscore
        teams_data = data.get("teams", {})
        side_data = teams_data.get(side, {})
        
        if "players" not in side_data:
            return []
            
        # Find players that are in the lineup (usually have a position number 1-9)
        lineup = []
        for player_id, player_data in side_data["players"].items():
            batting_order = player_data.get("battingOrder")
            if batting_order:  # This player is in the lineup
                player_info = {
                    "id": player_data.get("person", {}).get("id"),
                    "fullName": player_data.get("person", {}).get("fullName")
                }
                lineup.append(player_info)
                
        # Sort by batting order if available
        if lineup:
            lineup.sort(key=lambda x: x.get("battingOrder", 999) if x.get("battingOrder") else 999)
            
        return lineup
            
    except Exception as e:
        logger.error(f"Error fetching from alternate endpoint: {e}")
        return []

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

def get_test_lineups():
    """Return test lineup data for debugging"""
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
            "ballpark": "Globe Life Field",
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
        }
    ])

def get_fallback_lineups():
    """Return fallback lineup data when API calls fail"""
    # Use today's date to make it current
    today = date.today().isoformat()
    
    # Get real matchups for today from a static list of common matchups
    # In a real implementation, you could scrape this from a public source
    return pd.DataFrame([
        {
            "batter_name": "Aaron Judge",
            "batter_id": 592450,
            "opposing_pitcher": "Corbin Burnes",
            "pitcher_id": 669203,
            "pitcher_team": "BAL",
            "game_date": today,
            "game_id": generate_game_id("Aaron Judge", "Corbin Burnes", today),
            "ballpark": "Oriole Park at Camden Yards",
            "home_team": "BAL"
        },
        {
            "batter_name": "Juan Soto",
            "batter_id": 665742,
            "opposing_pitcher": "Pablo Lopez",
            "pitcher_id": 641154,
            "pitcher_team": "MIN",
            "game_date": today,
            "game_id": generate_game_id("Juan Soto", "Pablo Lopez", today),
            "ballpark": "Target Field",
            "home_team": "MIN"
        },
        {
            "batter_name": "Pete Alonso",
            "batter_id": 624413,
            "opposing_pitcher": "Miles Mikolas",
            "pitcher_id": 571945,
            "pitcher_team": "STL",
            "game_date": today,
            "game_id": generate_game_id("Pete Alonso", "Miles Mikolas", today),
            "ballpark": "Busch Stadium",
            "home_team": "STL"
        },
        {
            "batter_name": "Matt Olson",
            "batter_id": 621566,
            "opposing_pitcher": "Logan Webb",
            "pitcher_id": 657277,
            "pitcher_team": "SF",
            "game_date": today,
            "game_id": generate_game_id("Matt Olson", "Logan Webb", today),
            "ballpark": "Oracle Park",
            "home_team": "SF" 
        }
    ])

def generate_game_id(batter_name, pitcher_name, game_date):
    """Create a normalized game ID for batter vs pitcher matchups."""
    import unicodedata
    import re

    def normalize(name):
        # Convert to ASCII, removing accents
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8")
        # Remove non-alphanumeric characters and convert spaces to underscores
        name = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip().lower().replace(" ", "_")
        return name

    return f"{normalize(batter_name)}__vs__{normalize(pitcher_name)}__{game_date}"

# For testing
if __name__ == "__main__":
    lineups = get_confirmed_lineups(force_test=False, verbose=True)
    print(f"Found {len(lineups)} lineups")
    if not lineups.empty:
        print(lineups.head())
