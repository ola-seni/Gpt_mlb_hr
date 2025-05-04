#!/usr/bin/env python3
"""
Real-Time In-Game Adjustments for MLB HR Predictions
Adjusts predictions based on in-game factors like pitch count, game situation, and more
"""

import pandas as pd
import numpy as np
import requests
import os
import time
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/in_game.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("in_game")

class InGameAdjuster:
    """
    Adjusts HR predictions in real-time based on in-game factors
    """
    
    def __init__(self, cache_dir="cache/in_game"):
        """Initialize the in-game adjuster"""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.mlb_api_base = "https://statsapi.mlb.com/api"
        
        # Define adjustment factors
        self.adjustment_factors = {
            # Pitcher fatigue factor (based on pitch count)
            "pitch_count": {
                "ranges": [0, 25, 50, 75, 100, 125],
                "adjustments": [0.0, 0.0, 0.05, 0.08, 0.12, 0.15]
            },
            
            # Bullpen quality factor (based on bullpen ERA)
            "bullpen_quality": {
                "ranges": [0, 3.0, 3.5, 4.0, 4.5, 5.0],
                "adjustments": [-0.05, -0.03, 0.0, 0.03, 0.05, 0.08]
            },
            
            # Game score factor (based on run differential)
            "run_differential": {
                "ranges": [-5, -3, -1, 1, 3, 5],
                "adjustments": [0.03, 0.02, 0.0, -0.01, -0.02, 0.01]
            },
            
            # Leverage factor (based on game situation)
            "leverage": {
                "low": -0.02,     # Low leverage situation
                "medium": 0.0,    # Medium leverage
                "high": 0.03      # High leverage situation
            },
            
            # Ballpark weather factor (changes during game)
            "weather_change": {
                "warming": 0.02,   # Temperature increasing
                "cooling": -0.01,  # Temperature decreasing
                "wind_out": 0.03,  # Wind now blowing out
                "wind_in": -0.03   # Wind now blowing in
            }
        }
    
    def get_game_data(self, game_pk):
        """
        Get current game data from MLB Stats API
        
        Args:
            game_pk: MLB game ID
            
        Returns:
            dict: Game data
        """
        cache_file = os.path.join(self.cache_dir, f"game_{game_pk}.json")
        
        # Check for recent cache (less than 5 minutes old)
        if os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < 300:  # 5 minutes in seconds
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        # Fetch fresh data
        try:
            url = f"{self.mlb_api_base}/v1.1/game/{game_pk}/feed/live"
            logger.info(f"Fetching game data for {game_pk}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching game data: {e}")
            return None
    
    def calculate_pitcher_fatigue(self, game_data, pitcher_id):
        """
        Calculate pitcher fatigue factor based on pitch count
        
        Args:
            game_data: Game data from MLB Stats API
            pitcher_id: Pitcher ID to check
            
        Returns:
            float: Fatigue adjustment factor
        """
        if not game_data:
            return 0.0
            
        try:
            # Get current pitcher
            live_data = game_data.get("liveData", {})
            boxscore = live_data.get("boxscore", {})
            
            # Check both teams' players
            for team_side in ["home", "away"]:
                team_boxscore = boxscore.get("teams", {}).get(team_side, {})
                players = team_boxscore.get("players", {})
                
                # Look for our pitcher
                for player_id, player_data in players.items():
                    if player_data.get("person", {}).get("id") == pitcher_id:
                        # Found the pitcher
                        pitching_stats = player_data.get("stats", {}).get("pitching", {})
                        pitch_count = pitching_stats.get("pitchesThrown", 0)
                        
                        # Calculate fatigue factor
                        ranges = self.adjustment_factors["pitch_count"]["ranges"]
                        adjustments = self.adjustment_factors["pitch_count"]["adjustments"]
                        
                        # Find the appropriate range
                        for i in range(len(ranges)-1):
                            if ranges[i] <= pitch_count < ranges[i+1]:
                                return adjustments[i]
                        
                        # If over the highest range
                        if pitch_count >= ranges[-1]:
                            return adjustments[-1]
            
            # Pitcher not found or not currently in the game
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating pitcher fatigue: {e}")
            return 0.0
    
    def calculate_bullpen_factor(self, game_data, team_id):
        """
        Calculate bullpen factor based on team bullpen quality
        
        Args:
            game_data: Game data from MLB Stats API
            team_id: Team ID to check
            
        Returns:
            float: Bullpen adjustment factor
        """
        # This would ideally use real bullpen metrics
        # For simplicity, we'll use a fixed value based on team
        # In a full implementation, you would query team bullpen stats
        
        bullpen_eras = {
            # Example team bullpen ERAs
            "NYY": 3.2,
            "LAD": 3.1,
            "BOS": 4.2,
            "CHC": 3.8,
            "HOU": 3.0,
            "ATL": 3.4,
            "PHI": 4.0,
            "NYM": 3.7,
            "SFG": 3.5,
            "STL": 3.6
        }
        
        # Get ERA for the team or use average
        era = bullpen_eras.get(team_id, 4.0)
        
        # Calculate adjustment factor
        ranges = self.adjustment_factors["bullpen_quality"]["ranges"]
        adjustments = self.adjustment_factors["bullpen_quality"]["adjustments"]
        
        # Find the appropriate range
        for i in range(len(ranges)-1):
            if ranges[i] <= era < ranges[i+1]:
                return adjustments[i]
        
        # If over the highest range
        if era >= ranges[-1]:
            return adjustments[-1]
        
        return 0.0
    
    def calculate_game_situation_factor(self, game_data):
        """
        Calculate factor based on game situation (score, inning, etc.)
        
        Args:
            game_data: Game data from MLB Stats API
            
        Returns:
            dict: Game situation factors
        """
        if not game_data:
            return {"run_diff_factor": 0.0, "leverage_factor": 0.0}
            
        try:
            # Get game state
            live_data = game_data.get("liveData", {})
            linescore = live_data.get("linescore", {})
            
            # Get score
            home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
            away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
            
            # Calculate run differential
            run_diff = home_score - away_score
            
            # Get inning
            current_inning = linescore.get("currentInning", 1)
            inning_half = linescore.get("inningHalf", "top")
            
            # Calculate run differential factor
            run_diff_factor = 0.0
            ranges = self.adjustment_factors["run_differential"]["ranges"]
            adjustments = self.adjustment_factors["run_differential"]["adjustments"]
            
            # Find the appropriate range
            for i in range(len(ranges)-1):
                if ranges[i] <= run_diff < ranges[i+1]:
                    run_diff_factor = adjustments[i]
                    break
            
            # If over the highest range
            if run_diff >= ranges[-1]:
                run_diff_factor = adjustments[-1]
            
            # Calculate leverage factor
            leverage_factor = 0.0
            
            # Late game (7th inning or later)
            if current_inning >= 7:
                # Close game (within 2 runs)
                if abs(run_diff) <= 2:
                    leverage_factor = self.adjustment_factors["leverage"]["high"]
                # Medium game (within 4 runs)
                elif abs(run_diff) <= 4:
                    leverage_factor = self.adjustment_factors["leverage"]["medium"]
                # Blowout
                else:
                    leverage_factor = self.adjustment_factors["leverage"]["low"]
            # Middle game (4th-6th inning)
            elif current_inning >= 4:
                # Close game
                if abs(run_diff) <= 3:
                    leverage_factor = self.adjustment_factors["leverage"]["medium"]
                else:
                    leverage_factor = self.adjustment_factors["leverage"]["low"]
            # Early game
            else:
                leverage_factor = self.adjustment_factors["leverage"]["low"]
            
            return {
                "run_diff_factor": run_diff_factor,
                "leverage_factor": leverage_factor
            }
            
        except Exception as e:
            logger.error(f"Error calculating game situation factor: {e}")
            return {"run_diff_factor": 0.0, "leverage_factor": 0.0}
    
    def calculate_weather_change_factor(self, game_data, original_weather):
        """
        Calculate factor based on weather changes during the game
        
        Args:
            game_data: Game data from MLB Stats API
            original_weather: Original weather data at game start
            
        Returns:
            float: Weather change adjustment factor
        """
        # This would ideally use real-time weather data
        # For a real implementation, you would query a weather API
        
        # For now, we'll assume no change from the original weather
        return 0.0
    
    def apply_in_game_adjustments(self, predictions_df):
        """
        Apply in-game adjustments to HR predictions
        
        Args:
            predictions_df: DataFrame with HR predictions
            
        Returns:
            pandas.DataFrame: Adjusted predictions
        """
        if predictions_df.empty:
            return predictions_df
            
        logger.info(f"Applying in-game adjustments to {len(predictions_df)} predictions")
        
        # Make a copy to avoid modifying the original
        adjusted_df = predictions_df.copy()
        
        # Add new columns for adjustments
        adjusted_df["pitcher_fatigue"] = 0.0
        adjusted_df["bullpen_factor"] = 0.0
        adjusted_df["game_situation"] = 0.0
        adjusted_df["weather_change"] = 0.0
        adjusted_df["total_in_game_adjustment"] = 0.0
        adjusted_df["adjusted_HR_Score"] = adjusted_df["HR_Score"]
        
        # Process each game
        processed_games = set()
        
        for idx, row in adjusted_df.iterrows():
            try:
                game_id = str(row.get("game_id", ""))
                
                # Skip if no game ID
                if not game_id or pd.isna(game_id):
                    continue
                
                # Parse MLB game PK from our game ID (simplified approach)
                # In a real implementation, you would have a mapping from your game IDs to MLB game PKs
                game_pk = game_id.split('_')[-1] if '_' in game_id else "1"  # Fallback
                
                # Skip if already processed this game
                if game_pk in processed_games:
                    continue
                
                # Get game data
                game_data = self.get_game_data(game_pk)
                
                if not game_data:
                    continue
                
                processed_games.add(game_pk)
                
                # Get pitcher ID
                pitcher_id = row.get("pitcher_id")
                
                # Calculate adjustment factors
                pitcher_fatigue = self.calculate_pitcher_fatigue(game_data, pitcher_id)
                
                # Get team ID (simplified)
                pitcher_team = row.get("pitcher_team", "UNK")
                bullpen_factor = self.calculate_bullpen_factor(game_data, pitcher_team)
                
                # Get game situation factors
                situation_factors = self.calculate_game_situation_factor(game_data)
                run_diff_factor = situation_factors["run_diff_factor"]
                leverage_factor = situation_factors["leverage_factor"]
                
                # Get weather change factor
                original_weather = {}  # Would come from your weather data
                weather_change = self.calculate_weather_change_factor(game_data, original_weather)
                
                # Calculate total adjustment
                total_adjustment = (
                    pitcher_fatigue +
                    bullpen_factor +
                    run_diff_factor +
                    leverage_factor +
                    weather_change
                )
                
                # Apply to all batters in this game
                game_rows = adjusted_df[adjusted_df["game_id"] == game_id].index
                
                for row_idx in game_rows:
                    adjusted_df.at[row_idx, "pitcher_fatigue"] = pitcher_fatigue
                    adjusted_df.at[row_idx, "bullpen_factor"] = bullpen_factor
                    adjusted_df.at[row_idx, "game_situation"] = run_diff_factor + leverage_factor
                    adjusted_df.at[row_idx, "weather_change"] = weather_change
                    adjusted_df.at[row_idx, "total_in_game_adjustment"] = total_adjustment
                    
                    # Apply adjustment (multiplicative to preserve relative differences)
                    original_score = adjusted_df.at[row_idx, "HR_Score"]
                    adjusted_score = original_score * (1.0 + total_adjustment)
                    
                    # Ensure score stays in reasonable range
                    adjusted_df.at[row_idx, "adjusted_HR_Score"] = max(0.01, min(0.99, adjusted_score))
                
            except Exception as e:
                logger.error(f"Error processing in-game adjustments for row {idx}: {e}")
                continue
        
        logger.info(f"Applied in-game adjustments to {len(processed_games)} games")
        
        # Recalculate prediction tiers based on adjusted scores
        if "tag" in adjusted_df.columns:
            adjusted_df["adjusted_tag"] = adjusted_df["adjusted_HR_Score"].apply(
                lambda score: "Lock 🔒" if score >= 0.25 else 
                              "Sleeper 🌙" if score >= 0.15 else 
                              "Risky ⚠️"
            )
        
        return adjusted_df

def main():
    """Main function to apply in-game adjustments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply in-game adjustments to HR predictions")
    parser.add_argument("--input", type=str, required=True, help="Input CSV with predictions")
    parser.add_argument("--output", type=str, help="Output CSV for adjusted predictions")
    
    args = parser.parse_args()
    
    # Load predictions
    try:
        predictions_df = pd.read_csv(args.input)
        logger.info(f"Loaded {len(predictions_df)} predictions from {args.input}")
    except Exception as e:
        logger.error(f"Error loading predictions: {e}")
        return
    
    # Create adjuster
    adjuster = InGameAdjuster()
    
    # Apply adjustments
    adjusted_df = adjuster.apply_in_game_adjustments(predictions_df)
    
    # Save adjusted predictions
    output_path = args.output
    if not output_path:
        # Create output path based on input file
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_path = f"results/adjusted_{base_name}.csv"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    adjusted_df.to_csv(output_path, index=False)
    logger.info(f"Saved adjusted predictions to {output_path}")
    
    # Print summary
    adjustment_summary = adjusted_df["total_in_game_adjustment"].describe()
    print("\n========== In-Game Adjustment Summary ==========")
    print(f"Average adjustment: {adjustment_summary['mean']:.4f}")
    print(f"Min adjustment: {adjustment_summary['min']:.4f}")
    print(f"Max adjustment: {adjustment_summary['max']:.4f}")
    
    # Print examples of largest adjustments
    print("\nTop 5 largest positive adjustments:")
    top_adjusted = adjusted_df.sort_values("total_in_game_adjustment", ascending=False).head(5)
    for _, row in top_adjusted.iterrows():
        print(f"{row['batter_name']}: {row['HR_Score']:.3f} → {row['adjusted_HR_Score']:.3f} ({row['total_in_game_adjustment']*100:+.1f}%)")
    
    # Print changes in prediction tiers
    if "tag" in adjusted_df.columns and "adjusted_tag" in adjusted_df.columns:
        changed_tiers = adjusted_df[adjusted_df["tag"] != adjusted_df["adjusted_tag"]]
        print(f"\n{len(changed_tiers)} predictions changed tiers after in-game adjustments")

if __name__ == "__main__":
    main()
