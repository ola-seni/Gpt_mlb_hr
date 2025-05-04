#!/usr/bin/env python3
"""
Pitch-by-Pitch Data Collector for Enhanced MLB HR Prediction
This script collects detailed pitch-by-pitch data for more accurate plate discipline metrics
"""

import pandas as pd
import requests
import json
import os
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/pitch_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pitch_data")

class PitchDataCollector:
    """Collects detailed pitch-by-pitch data from MLB Stats API"""
    
    def __init__(self, cache_dir="cache/pitch_data"):
        """Initialize the collector"""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.mlb_api_base = "https://statsapi.mlb.com/api"
        
    def get_games_for_date(self, date_str):
        """Get all MLB games for a specific date"""
        try:
            url = f"{self.mlb_api_base}/v1/schedule?sportId=1&date={date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            games = []
            
            if "dates" in data and len(data["dates"]) > 0:
                for game in data["dates"][0].get("games", []):
                    games.append({
                        "game_pk": game["gamePk"],
                        "away_team": game["teams"]["away"]["team"]["name"],
                        "home_team": game["teams"]["home"]["team"]["name"],
                        "game_date": game["gameDate"]
                    })
            
            return games
        except Exception as e:
            logger.error(f"Error fetching games for {date_str}: {e}")
            return []
    
    def get_pitch_data_for_game(self, game_pk):
        """Get pitch-by-pitch data for a specific game"""
        # Check cache first
        cache_file = os.path.join(self.cache_dir, f"game_{game_pk}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                # If cache is corrupted, continue to fetch fresh data
                pass
        
        try:
            url = f"{self.mlb_api_base}/v1.1/game/{game_pk}/feed/live"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            return data
        except Exception as e:
            logger.error(f"Error fetching pitch data for game {game_pk}: {e}")
            return None
    
    def extract_pitch_metrics(self, game_data):
        """Extract pitch-by-pitch metrics from game data"""
        if not game_data or "liveData" not in game_data:
            return []
        
        try:
            all_plays = game_data["liveData"]["plays"]["allPlays"]
            pitch_metrics = []
            
            for play in all_plays:
                # Get at-bat info
                about = play.get("about", {})
                matchup = play.get("matchup", {})
                
                batter_id = matchup.get("batter", {}).get("id")
                batter_name = matchup.get("batter", {}).get("fullName")
                pitcher_id = matchup.get("pitcher", {}).get("id")
                pitcher_name = matchup.get("pitcher", {}).get("fullName")
                
                # Get all pitches in this at-bat
                play_events = play.get("playEvents", [])
                
                for event in play_events:
                    # Filter for pitch events
                    if event.get("isPitch"):
                        pitch_data = {
                            "game_pk": game_data["gameData"]["game"]["pk"],
                            "game_date": game_data["gameData"]["game"]["calendarEventTime"],
                            "inning": about.get("inning"),
                            "inning_half": about.get("halfInning"),
                            "count_balls": event.get("count", {}).get("balls"),
                            "count_strikes": event.get("count", {}).get("strikes"),
                            "batter_id": batter_id,
                            "batter_name": batter_name,
                            "pitcher_id": pitcher_id,
                            "pitcher_name": pitcher_name,
                            "pitch_type": event.get("details", {}).get("type", {}).get("code"),
                            "pitch_name": event.get("details", {}).get("type", {}).get("description"),
                            "pitch_speed": event.get("pitchData", {}).get("startSpeed"),
                            "zone": event.get("pitchData", {}).get("zone"),
                            "call_type": event.get("details", {}).get("call", {}).get("code"),
                            "call_desc": event.get("details", {}).get("call", {}).get("description"),
                            "result_type": event.get("details", {}).get("event"),
                            "result_desc": event.get("details", {}).get("description"),
                            "in_zone": event.get("pitchData", {}).get("zone") <= 9 if event.get("pitchData", {}).get("zone") is not None else None,
                            "is_swing": "swing" in (event.get("details", {}).get("description", "").lower() or ""),
                            "is_contact": any(s in (event.get("details", {}).get("description", "").lower() or "") 
                                           for s in ["hit", "foul", "play"]),
                            "exit_velo": event.get("hitData", {}).get("launchSpeed"),
                            "launch_angle": event.get("hitData", {}).get("launchAngle"),
                            "hit_distance": event.get("hitData", {}).get("totalDistance")
                        }
                        
                        pitch_metrics.append(pitch_data)
            
            return pitch_metrics
        except Exception as e:
            logger.error(f"Error extracting pitch metrics: {e}")
            return []
    
    def collect_data_for_date_range(self, start_date, end_date=None):
        """Collect pitch data for a date range"""
        if end_date is None:
            end_date = start_date
            
        # Convert to datetime objects
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_dt = start_dt
        all_pitch_data = []
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            logger.info(f"Collecting pitch data for {date_str}")
            
            # Get games for this date
            games = self.get_games_for_date(date_str)
            logger.info(f"Found {len(games)} games for {date_str}")
            
            for game in games:
                game_pk = game["game_pk"]
                logger.info(f"Collecting pitch data for game {game_pk}: {game['away_team']} @ {game['home_team']}")
                
                # Get pitch data
                game_data = self.get_pitch_data_for_game(game_pk)
                
                # Extract metrics
                if game_data:
                    pitch_metrics = self.extract_pitch_metrics(game_data)
                    all_pitch_data.extend(pitch_metrics)
                    logger.info(f"Extracted {len(pitch_metrics)} pitch metrics from game {game_pk}")
                
                # Be nice to the API
                time.sleep(1)
            
            current_dt += timedelta(days=1)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_pitch_data)
        
        # Save to CSV
        os.makedirs("data", exist_ok=True)
        output_file = f"data/pitch_data_{start_date}_to_{end_date}.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(df)} pitch metrics to {output_file}")
        
        return df
    
    def generate_plate_discipline_metrics(self, pitch_data):
        """Generate enhanced plate discipline metrics from pitch-by-pitch data"""
        if pitch_data.empty:
            return pd.DataFrame()
            
        # Group by batter
        batter_metrics = []
        
        for batter_id, group in pitch_data.groupby("batter_id"):
            # Total pitches
            total_pitches = len(group)
            
            # Zone metrics
            in_zone = group['in_zone'].sum()
            zone_pct = in_zone / total_pitches if total_pitches > 0 else 0
            
            # Swing metrics
            swings = group['is_swing'].sum()
            swing_pct = swings / total_pitches if total_pitches > 0 else 0
            
            # Contact metrics
            contacts = group['is_contact'].sum()
            contact_pct = contacts / swings if swings > 0 else 0
            
            # Zone breakdown
            zone_pitches = group[group['in_zone'] == True]
            outside_pitches = group[group['in_zone'] == False]
            
            zone_swings = zone_pitches['is_swing'].sum()
            outside_swings = outside_pitches['is_swing'].sum()
            
            z_swing_pct = zone_swings / len(zone_pitches) if len(zone_pitches) > 0 else 0
            o_swing_pct = outside_swings / len(outside_pitches) if len(outside_pitches) > 0 else 0
            
            # Add to metrics
            batter_metrics.append({
                "batter_id": batter_id,
                "batter_name": group["batter_name"].iloc[0],
                "total_pitches": total_pitches,
                "zone_pct": round(zone_pct, 3),
                "swing_pct": round(swing_pct, 3),
                "contact_pct": round(contact_pct, 3),
                "z_swing_pct": round(z_swing_pct, 3),
                "o_swing_pct": round(o_swing_pct, 3),
                "chase_diff": round(z_swing_pct - o_swing_pct, 3),  # Zone discipline
                "pitch_recognition": round((1 - o_swing_pct) * swing_pct, 3)  # New composite metric
            })
        
        return pd.DataFrame(batter_metrics)

def main():
    """Main function to run the data collector"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Collect pitch-by-pitch data for MLB games")
    parser.add_argument("--start_date", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--analyze", action="store_true", help="Generate plate discipline metrics")
    
    args = parser.parse_args()
    
    # Create collector
    collector = PitchDataCollector()
    
    # Collect data
    pitch_data = collector.collect_data_for_date_range(args.start_date, args.end_date)
    
    # Generate metrics if requested
    if args.analyze and not pitch_data.empty:
        metrics = collector.generate_plate_discipline_metrics(pitch_data)
        metrics_file = f"data/plate_discipline_{args.start_date}_to_{args.end_date or args.start_date}.csv"
        metrics.to_csv(metrics_file, index=False)
        logger.info(f"Saved plate discipline metrics to {metrics_file}")
        
        # Print summary
        print("\n========== Plate Discipline Metrics Summary ==========")
        print(metrics[["batter_name", "swing_pct", "contact_pct", "z_swing_pct", "o_swing_pct"]].head(10))

if __name__ == "__main__":
    main()
