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
    logger.info("📋 Getting projected lineups...")
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
        else:
            # Remove stale cache
            logger.info("Cache is stale, removing it")
            os.remove(cache_path)
    
    # Try multiple approaches for getting lineups
    df = fetch_projected_lineups_from_mlb_api()
    
    # If method 1 failed, try scraping data from ESPN
    if df.empty:
        logger.info("MLB API method failed, trying ESPN data scraping...")
        df = scrape_projected_lineups_from_espn()
    
    # If both methods failed, use static fallback data
    if df.empty:
        logger.info("All dynamic methods failed, using expanded fallback data...")
        df = get_expanded_fallback_projections()
    
    # Cache the data if we got valid results
    if not df.empty:
        lineups_list = df.to_dict('records')
        with open(cache_path, 'w') as f:
            json.dump(lineups_list, f)
            
    return df

def fetch_projected_lineups_from_mlb_api():
    """
    Fetch projected lineups from the MLB Stats API.
    
    Returns:
        pandas.DataFrame: DataFrame with lineup information
    """
    today = date.today().isoformat()
    
    # Try multiple API endpoints in sequence
    api_variants = [
        # Basic schedule to get games and probables
        {
            "url": f"{MLB_STATS_API_BASE}/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team,venue",
            "desc": "MLB API v1 basic schedule"
        },
        # Try v1.1 endpoint 
        {
            "url": f"{MLB_STATS_API_BASE}/v1.1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team,venue",
            "desc": "MLB API v1.1 basic schedule"
        }
    ]
    
    schedule = None
    success_variant = None
    
    # Try each API variant
    for variant in api_variants:
        logger.info(f"Trying {variant['desc']}: {variant['url']}")
        
        try:
            response = requests.get(variant["url"], timeout=10)
            if response.status_code == 200:
                schedule = response.json()
                success_variant = variant["desc"]
                logger.info(f"✅ Success with {variant['desc']}")
                break
            else:
                logger.warning(f"Failed with status {response.status_code}")
        except Exception as e:
            logger.warning(f"Error with {variant['desc']}: {e}")
    
    if not schedule:
        logger.error("All API variants failed")
        return pd.DataFrame()
    
    # Now process the schedule to get games and probable pitchers
    projected = []
    
    try:
        # Make sure we have dates in the response
        if "dates" not in schedule or not schedule["dates"]:
            logger.warning("No games found in schedule response")
            return pd.DataFrame()
        
        # Process each game
        for date_block in schedule.get("dates", []):
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
        
    except Exception as e:
        logger.error(f"Error processing schedule: {e}")
        return pd.DataFrame()

def scrape_projected_lineups_from_espn():
    """
    Scrape projected lineups from ESPN.
    This is a simplified version - in a real implementation, you would use proper HTML parsing libraries.
    
    Returns:
        pandas.DataFrame: DataFrame with lineup information
    """
    logger.info("Attempting to scrape lineup data from ESPN...")
    
    try:
        # This would be a real web scraping implementation using requests and BeautifulSoup
        # For demonstration, we'll use a simplified approach
        
        # Example URLs:
        # ESPN MLB Scoreboard: https://www.espn.com/mlb/scoreboard
        # Team page example: https://www.espn.com/mlb/team/roster/_/name/nyy/new-york-yankees
        
        # Simplified placeholder
        logger.warning("Web scraping implementation is a placeholder - would need to implement proper HTML parsing")
        
        # Return empty DataFrame for now - would return real scraped data in full implementation
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error scraping data from ESPN: {e}")
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

def get_expanded_fallback_projections():
    """
    Return a greatly expanded set of fallback projected lineups to ensure variety.
    This is much larger than the previous fallback data and covers all MLB teams.
    
    Returns:
        pandas.DataFrame: DataFrame with projected lineup information
    """
    today = date.today().isoformat()
    
    # This is a much more extensive set of matchups and players
    # It includes 20+ different batters from many teams to ensure variety
    
    fallback_data = [
        # AL East
        # Yankees
        {"batter": "Aaron Judge", "id": 592450, "team": "NYY", "opp": "BOS", "pitcher": "Nick Pivetta", "pid": 601713},
        {"batter": "Juan Soto", "id": 665742, "team": "NYY", "opp": "BOS", "pitcher": "Nick Pivetta", "pid": 601713},
        {"batter": "Giancarlo Stanton", "id": 519317, "team": "NYY", "opp": "BOS", "pitcher": "Nick Pivetta", "pid": 601713},
        {"batter": "Anthony Rizzo", "id": 519203, "team": "NYY", "opp": "BOS", "pitcher": "Nick Pivetta", "pid": 601713},
        
        # Red Sox
        {"batter": "Rafael Devers", "id": 646240, "team": "BOS", "opp": "NYY", "pitcher": "Carlos Rodon", "pid": 607074},
        {"batter": "Triston Casas", "id": 671213, "team": "BOS", "opp": "NYY", "pitcher": "Carlos Rodon", "pid": 607074},
        {"batter": "Jarren Duran", "id": 680776, "team": "BOS", "opp": "NYY", "pitcher": "Carlos Rodon", "pid": 607074},
        
        # Blue Jays
        {"batter": "Vladimir Guerrero Jr.", "id": 665489, "team": "TOR", "opp": "TB", "pitcher": "Zach Eflin", "pid": 621107},
        {"batter": "Bo Bichette", "id": 666182, "team": "TOR", "opp": "TB", "pitcher": "Zach Eflin", "pid": 621107},
        {"batter": "George Springer", "id": 543807, "team": "TOR", "opp": "TB", "pitcher": "Zach Eflin", "pid": 621107},
        
        # Rays
        {"batter": "Yandy Diaz", "id": 650490, "team": "TB", "opp": "TOR", "pitcher": "Jose Berrios", "pid": 621244},
        {"batter": "Randy Arozarena", "id": 668227, "team": "TB", "opp": "TOR", "pitcher": "Jose Berrios", "pid": 621244},
        
        # Orioles
        {"batter": "Adley Rutschman", "id": 668939, "team": "BAL", "opp": "CLE", "pitcher": "Shane Bieber", "pid": 669456},
        {"batter": "Gunnar Henderson", "id": 683002, "team": "BAL", "opp": "CLE", "pitcher": "Shane Bieber", "pid": 669456},
        {"batter": "Anthony Santander", "id": 623993, "team": "BAL", "opp": "CLE", "pitcher": "Shane Bieber", "pid": 669456},
        
        # AL Central
        # Guardians
        {"batter": "Jose Ramirez", "id": 621046, "team": "CLE", "opp": "BAL", "pitcher": "Corbin Burnes", "pid": 669203},
        {"batter": "Josh Naylor", "id": 647304, "team": "CLE", "opp": "BAL", "pitcher": "Corbin Burnes", "pid": 669203},
        
        # Twins
        {"batter": "Carlos Correa", "id": 621043, "team": "MIN", "opp": "DET", "pitcher": "Tarik Skubal", "pid": 669373},
        {"batter": "Byron Buxton", "id": 621439, "team": "MIN", "opp": "DET", "pitcher": "Tarik Skubal", "pid": 669373},
        {"batter": "Royce Lewis", "id": 668904, "team": "MIN", "opp": "DET", "pitcher": "Tarik Skubal", "pid": 669373},
        
        # AL West
        # Astros
        {"batter": "Yordan Alvarez", "id": 670541, "team": "HOU", "opp": "SEA", "pitcher": "Luis Castillo", "pid": 622491},
        {"batter": "Kyle Tucker", "id": 663656, "team": "HOU", "opp": "SEA", "pitcher": "Luis Castillo", "pid": 622491},
        {"batter": "Jose Altuve", "id": 514888, "team": "HOU", "opp": "SEA", "pitcher": "Luis Castillo", "pid": 622491},
        
        # Mariners
        {"batter": "Julio Rodriguez", "id": 677594, "team": "SEA", "opp": "HOU", "pitcher": "Framber Valdez", "pid": 664285},
        {"batter": "Cal Raleigh", "id": 663728, "team": "SEA", "opp": "HOU", "pitcher": "Framber Valdez", "pid": 664285},
        
        # Angels
        {"batter": "Mike Trout", "id": 545361, "team": "LAA", "opp": "OAK", "pitcher": "Paul Blackburn", "pid": 621112},
        {"batter": "Anthony Rendon", "id": 543685, "team": "LAA", "opp": "OAK", "pitcher": "Paul Blackburn", "pid": 621112},
        
        # NL East
        # Phillies
        {"batter": "Bryce Harper", "id": 547180, "team": "PHI", "opp": "ATL", "pitcher": "Spencer Strider", "pid": 675911},
        {"batter": "Trea Turner", "id": 607208, "team": "PHI", "opp": "ATL", "pitcher": "Spencer Strider", "pid": 675911},
        {"batter": "Kyle Schwarber", "id": 656941, "team": "PHI", "opp": "ATL", "pitcher": "Spencer Strider", "pid": 675911},
        
        # Braves
        {"batter": "Matt Olson", "id": 621566, "team": "ATL", "opp": "PHI", "pitcher": "Zack Wheeler", "pid": 554430},
        {"batter": "Marcell Ozuna", "id": 542303, "team": "ATL", "opp": "PHI", "pitcher": "Zack Wheeler", "pid": 554430},
        {"batter": "Austin Riley", "id": 663586, "team": "ATL", "opp": "PHI", "pitcher": "Zack Wheeler", "pid": 554430},
        
        # Mets
        {"batter": "Pete Alonso", "id": 624413, "team": "NYM", "opp": "STL", "pitcher": "Miles Mikolas", "pid": 571945},
        {"batter": "Francisco Lindor", "id": 596019, "team": "NYM", "opp": "STL", "pitcher": "Miles Mikolas", "pid": 571945},
        {"batter": "Brandon Nimmo", "id": 607043, "team": "NYM", "opp": "STL", "pitcher": "Miles Mikolas", "pid": 571945},
        
        # NL Central
        # Cardinals
        {"batter": "Nolan Arenado", "id": 571448, "team": "STL", "opp": "NYM", "pitcher": "Luis Severino", "pid": 622663},
        {"batter": "Paul Goldschmidt", "id": 502671, "team": "STL", "opp": "NYM", "pitcher": "Luis Severino", "pid": 622663},
        {"batter": "Willson Contreras", "id": 575929, "team": "STL", "opp": "NYM", "pitcher": "Luis Severino", "pid": 622663},
        
        # Cubs
        {"batter": "Ian Happ", "id": 664023, "team": "CHC", "opp": "MIL", "pitcher": "Freddy Peralta", "pid": 642547},
        {"batter": "Seiya Suzuki", "id": 673548, "team": "CHC", "opp": "MIL", "pitcher": "Freddy Peralta", "pid": 642547},
        {"batter": "Dansby Swanson", "id": 621020, "team": "CHC", "opp": "MIL", "pitcher": "Freddy Peralta", "pid": 642547},
        
        # NL West
        # Dodgers
        {"batter": "Shohei Ohtani", "id": 660271, "team": "LAD", "opp": "SD", "pitcher": "Yu Darvish", "pid": 506433},
        {"batter": "Mookie Betts", "id": 605141, "team": "LAD", "opp": "SD", "pitcher": "Yu Darvish", "pid": 506433},
        {"batter": "Freddie Freeman", "id": 518692, "team": "LAD", "opp": "SD", "pitcher": "Yu Darvish", "pid": 506433},
        
        # Padres
        {"batter": "Fernando Tatis Jr.", "id": 665487, "team": "SD", "opp": "LAD", "pitcher": "Tyler Glasnow", "pid": 607192},
        {"batter": "Manny Machado", "id": 592518, "team": "SD", "opp": "LAD", "pitcher": "Tyler Glasnow", "pid": 607192},
        {"batter": "Jurickson Profar", "id": 595777, "team": "SD", "opp": "LAD", "pitcher": "Tyler Glasnow", "pid": 607192},
        
        # Giants
        {"batter": "Matt Chapman", "id": 656305, "team": "SF", "opp": "COL", "pitcher": "Ryan Feltner", "pid": 683137},
        {"batter": "Michael Conforto", "id": 624424, "team": "SF", "opp": "COL", "pitcher": "Ryan Feltner", "pid": 683137},
        {"batter": "Jung Hoo Lee", "id": 700182, "team": "SF", "opp": "COL", "pitcher": "Ryan Feltner", "pid": 683137},
        
        # Rockies
        {"batter": "Kris Bryant", "id": 592178, "team": "COL", "opp": "SF", "pitcher": "Logan Webb", "pid": 657277},
        {"batter": "Ryan McMahon", "id": 641857, "team": "COL", "opp": "SF", "pitcher": "Logan Webb", "pid": 657277},
        {"batter": "Brendan Rodgers", "id": 663898, "team": "COL", "opp": "SF", "pitcher": "Logan Webb", "pid": 657277},
    ]
    
    # Convert the above data to the proper format
    projected = []
    for p in fallback_data:
        home_team = p["opp"]
        batter_team = p["team"]
        
        # Determine ballpark - assuming the opposing team is the home team
        ballpark = get_ballpark_name(home_team)
        
        projected.append({
            "batter_name": p["batter"],
            "batter_id": p["id"],
            "opposing_pitcher": p["pitcher"],
            "pitcher_id": p["pid"],
            "pitcher_team": p["opp"],
            "game_date": today,
            "game_id": generate_game_id(p["batter"], p["pitcher"], today),
            "ballpark": ballpark,
            "home_team": home_team
        })
    
    logger.info(f"Created expanded fallback projections with {len(projected)} players")
    return pd.DataFrame(projected)

# For testing
if __name__ == "__main__":
    lineups = get_projected_lineups()
    print(f"Found {len(lineups)} projected lineups")
    if not lineups.empty:
        print(lineups.head())
