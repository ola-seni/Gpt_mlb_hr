#!/usr/bin/env python3
"""
MLB API Test Script
This script tests the connections to the MLB Stats API and diagnoses issues.
"""

import requests
import json
import logging
import os
import time
from datetime import datetime, date

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mlb_api_test.log")
    ]
)
logger = logging.getLogger("mlb_api_test")

# Constants
MLB_STATS_API_BASE = "https://statsapi.mlb.com/api"
TEST_DIR = "test_results"
os.makedirs(TEST_DIR, exist_ok=True)

def test_mlb_api_endpoints():
    """Test various MLB Stats API endpoints for connectivity and data quality."""
    today = date.today().isoformat()
    
    endpoints = [
        {
            "name": "Schedule (Basic)",
            "url": f"{MLB_STATS_API_BASE}/v1/schedule?sportId=1&date={today}",
            "expected_keys": ["dates", "totalGames", "totalGamesInProgress"]
        },
        {
            "name": "Schedule (Hydrated)",
            "url": f"{MLB_STATS_API_BASE}/v1/schedule?sportId=1&date={today}&hydrate=lineups,probablePitcher,venue",
            "expected_keys": ["dates", "totalGames"]
        },
        {
            "name": "Teams",
            "url": f"{MLB_STATS_API_BASE}/v1/teams?sportId=1",
            "expected_keys": ["teams"]
        }
    ]
    
    results = []
    
    for endpoint in endpoints:
        logger.info(f"Testing endpoint: {endpoint['name']}")
        
        try:
            start_time = time.time()
            response = requests.get(endpoint["url"], timeout=10)
            response_time = time.time() - start_time
            
            status = {
                "name": endpoint["name"],
                "url": endpoint["url"],
                "status_code": response.status_code,
                "response_time": f"{response_time:.2f}s",
                "success": False,
                "error": None,
                "data_quality": {}
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for expected keys
                    missing_keys = [key for key in endpoint["expected_keys"] if key not in data]
                    
                    if not missing_keys:
                        status["success"] = True
                        
                        # Check data quality
                        if "dates" in data and data["dates"]:
                            status["data_quality"]["games_found"] = len(data["dates"][0].get("games", []))
                            
                            # Check for lineups
                            if status["data_quality"]["games_found"] > 0:
                                first_game = data["dates"][0]["games"][0]
                                
                                # Check for home lineup
                                home_lineup = first_game.get("teams", {}).get("home", {}).get("lineup", {})
                                status["data_quality"]["has_home_lineup"] = bool(home_lineup)
                                
                                # Check for probable pitchers
                                home_pitcher = first_game.get("teams", {}).get("home", {}).get("probablePitcher", {})
                                status["data_quality"]["has_home_pitcher"] = bool(home_pitcher.get("id"))
                    else:
                        status["error"] = f"Missing expected keys: {', '.join(missing_keys)}"
                        
                except json.JSONDecodeError:
                    status["error"] = "Invalid JSON response"
            else:
                status["error"] = f"HTTP error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            status["status_code"] = "Error"
            status["error"] = str(e)
            
        results.append(status)
        logger.info(f"Result: {'✅ Success' if status['success'] else '❌ Failed'} - {status.get('error', '')}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = os.path.join(TEST_DIR, f"api_test_{timestamp}.json")
    
    with open(result_path, "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Test results saved to {result_path}")
    return results

def test_weather_api():
    """Test the OpenWeather API connection."""
    from dotenv import load_dotenv
    load_dotenv()
    
    OPENWEATHER_API = os.getenv("OPENWEATHER_API")
    
    if not OPENWEATHER_API:
        logger.warning("⚠️ OpenWeather API key not found in environment variables")
        return False
    
    test_locations = [
        "New York,US",
        "Los Angeles,US",
        "Chicago,US"
    ]
    
    success = True
    
    for location in test_locations:
        logger.info(f"Testing weather API for location: {location}")
        
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API}&units=metric"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Weather API success: {location} - Temp: {data.get('main', {}).get('temp')}°C")
            else:
                logger.error(f"❌ Weather API failed for {location}: HTTP {response.status_code}")
                success = False
                
        except Exception as e:
            logger.error(f"❌ Weather API error for {location}: {e}")
            success = False
    
    return success

def analyze_lineup_issues():
    """Analyze specific issues with lineups."""
    today = date.today().isoformat()
    url = f"{MLB_STATS_API_BASE}/v1/schedule?sportId=1&date={today}&hydrate=lineups,probablePitcher,venue"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"❌ HTTP error: {response.status_code}")
            return
            
        data = response.json()
        
        if "dates" not in data or not data["dates"]:
            logger.warning("⚠️ No games found for today")
            return
            
        games = data["dates"][0].get("games", [])
        
        if not games:
            logger.warning("⚠️ No games found for today")
            return
            
        logger.info(f"Found {len(games)} games scheduled for today")
        
        lineup_issues = []
        
        for game_idx, game in enumerate(games):
            game_pk = game.get("gamePk", f"Game {game_idx+1}")
            teams = game.get("teams", {})
            
            for side in ["home", "away"]:
                team_data = teams.get(side, {})
                team_name = team_data.get("team", {}).get("name", f"{side.capitalize()} Team")
                
                # Check for lineup existence and structure
                has_lineup = False
                lineup_structure = "Unknown"
                
                if "lineup" in team_data:
                    has_lineup = True
                    
                    # Check different possible lineup structures
                    lineup = team_data["lineup"]
                    
                    if isinstance(lineup, dict) and "expected" in lineup:
                        lineup_structure = "Expected/Actual Structure"
                        players = lineup.get("expected", {}).get("lineup", [])
                    elif isinstance(lineup, list):
                        lineup_structure = "Direct List Structure"
                        players = lineup
                    else:
                        lineup_structure = f"Unknown Structure: {type(lineup)}"
                        players = []
                        
                    # Check player data structure in lineup
                    if players:
                        player_example = players[0]
                        player_structure = []
                        
                        if "fullName" in player_example:
                            player_structure.append("fullName")
                        if "id" in player_example:
                            player_structure.append("id")
                        if "person" in player_example:
                            player_structure.append("person.fullName")
                            player_structure.append("person.id")
                            
                lineup_issues.append({
                    "game_pk": game_pk,
                    "team": team_name,
                    "side": side,
                    "has_lineup": has_lineup,
                    "lineup_structure": lineup_structure,
                    "player_structure": player_structure if has_lineup and "player_structure" in locals() else [],
                    "player_count": len(players) if has_lineup and "players" in locals() else 0
                })
        
        # Save lineup analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_path = os.path.join(TEST_DIR, f"lineup_analysis_{timestamp}.json")
        
        with open(result_path, "w") as f:
            json.dump(lineup_issues, f, indent=2)
            
        logger.info(f"Lineup analysis saved to {result_path}")
        
    except Exception as e:
        logger.error(f"❌ Error analyzing lineups: {e}")

def main():
    """Main function to run all tests."""
    logger.info("🔍 Starting MLB API Tests")
    
    # Test MLB API endpoints
    api_results = test_mlb_api_endpoints()
    
    # Test weather API
    weather_success = test_weather_api()
    
    # Analyze lineup issues
    analyze_lineup_issues()
    
    # Print summary
    logger.info("\n🔍 Test Summary:")
    
    endpoint_success = sum(1 for result in api_results if result["success"])
    logger.info(f"MLB API Endpoints: {endpoint_success}/{len(api_results)} succeeded")
    
    logger.info(f"Weather API: {'✅ Success' if weather_success else '❌ Failed'}")
    
    logger.info("\n📋 Recommendations:")
    
    if endpoint_success < len(api_results):
        logger.info("- Check MLB API connectivity and update endpoints if needed")
        
    if not weather_success:
        logger.info("- Add OPENWEATHER_API key to your .env file")
        
    logger.info("- Check test_results directory for detailed reports")
    logger.info("- Update lineup_parser.py to handle the lineup structures found in the analysis")

if __name__ == "__main__":
    main()
