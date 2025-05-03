# game_state_monitor.py
import requests
import logging
import json
import os
import time
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/game_state.log',
    filemode='a'
)
logger = logging.getLogger("game_state")

class GameStateMonitor:
    """Monitor MLB game states and get in-game data"""
    
    def __init__(self, cache_dir="cache/game_state"):
        """
        Initialize the game state monitor.
        
        Args:
            cache_dir (str): Directory to cache game state data
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.mlb_api_base = "https://statsapi.mlb.com/api"
        
    def get_live_game_data(self, game_pk):
        """
        Get live data for a specific game.
        
        Args:
            game_pk (str): MLB game ID
            
        Returns:
            dict: Game state data
        """
        cache_file = os.path.join(self.cache_dir, f"game_{game_pk}.json")
        
        # Check for recent cache (less than 5 minutes old)
        if os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < 300:  # 5 minutes in seconds
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error reading cache file: {e}")
        
        # Fetch fresh data
        try:
            url = f"{self.mlb_api_base}/v1.1/game/{game_pk}/feed/live"
            logger.info(f"Fetching live data for game {game_pk}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching live game data for {game_pk}: {e}")
            return None
    
    def get_game_context_factors(self, game_pk):
        """
        Extract useful in-game context factors for prediction.
        
        Args:
            game_pk (str): MLB game ID
            
        Returns:
            dict: Context factors for prediction
        """
        data = self.get_live_game_data(game_pk)
        if not data:
            return {}
        
        context = {}
        
        try:
            # Get basic game state
            live_data = data.get("liveData", {})
            plays = live_data.get("plays", {})
            current_play = plays.get("currentPlay", {})
            
            # Game state
            context["inning"] = current_play.get("about", {}).get("inning", 1)
            context["inning_half"] = current_play.get("about", {}).get("halfInning", "top")
            context["outs"] = current_play.get("count", {}).get("outs", 0)
            
            # Score
            linescore = live_data.get("linescore", {})
            context["home_score"] = linescore.get("teams", {}).get("home", {}).get("runs", 0)
            context["away_score"] = linescore.get("teams", {}).get("away", {}).get("runs", 0)
            context["score_differential"] = abs(context["home_score"] - context["away_score"])
            
            # Baserunners
            runners = current_play.get("matchup", {}).get("runners", [])
            context["runners_on"] = len(runners)
            context["runners_in_scoring"] = sum(1 for r in runners if r.get("status", {}).get("code", 0) in [2, 3])
            
            # Current pitcher stats
            pitcher = current_play.get("matchup", {}).get("pitcher", {})
            context["current_pitcher_id"] = pitcher.get("id")
            context["starter_replaced"] = self._is_starter_replaced(data, context["current_pitcher_id"])
            
            # Pitcher fatigue estimation
            if context["starter_replaced"]:
                context["pitcher_fatigue"] = 0.1  # Fresh reliever
            else:
                # Estimate starter fatigue based on pitch count
                pitch_count = self._get_pitcher_pitch_count(data, context["current_pitcher_id"])
                context["pitch_count"] = pitch_count
                context["pitcher_fatigue"] = min(1.0, max(0.0, (pitch_count - 60) / 40))
            
            return context
            
        except Exception as e:
            logger.error(f"Error extracting game context: {e}")
            return {}
    
    def _is_starter_replaced(self, game_data, current_pitcher_id):
        """Check if the current pitcher is a reliever"""
        try:
            # Get starting pitchers
            boxscore = game_data.get("liveData", {}).get("boxscore", {})
            home_starter = boxscore.get("teams", {}).get("home", {}).get("pitchers", [])[0]
            away_starter = boxscore.get("teams", {}).get("away", {}).get("pitchers", [])[0]
            
            return str(current_pitcher_id) not in [str(home_starter), str(away_starter)]
            
        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Error checking if starter replaced: {e}")
            return False
    
    def _get_pitcher_pitch_count(self, game_data, pitcher_id):
        """Get the current pitch count for the pitcher"""
        try:
            # Look for the pitcher in the boxscore
            boxscore = game_data.get("liveData", {}).get("boxscore", {})
            
            # Check home pitchers
            home_pitcher_stats = boxscore.get("teams", {}).get("home", {}).get("players", {})
            for player_id, stats in home_pitcher_stats.items():
                if str(stats.get("person", {}).get("id")) == str(pitcher_id):
                    return stats.get("stats", {}).get("pitching", {}).get("pitchesThrown", 0)
            
            # Check away pitchers
            away_pitcher_stats = boxscore.get("teams", {}).get("away", {}).get("players", {})
            for player_id, stats in away_pitcher_stats.items():
                if str(stats.get("person", {}).get("id")) == str(pitcher_id):
                    return stats.get("stats", {}).get("pitching", {}).get("pitchesThrown", 0)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting pitcher pitch count: {e}")
            return 0
    
    def enhance_predictions_with_game_state(self, predictions_df):
        """
        Enhance HR predictions with game context data.
        
        Args:
            predictions_df (pandas.DataFrame): DataFrame with baseline predictions
            
        Returns:
            pandas.DataFrame: Enhanced predictions with game state factors
        """
        enhanced_df = predictions_df.copy()
        
        # Get game context for each unique game
        game_contexts = {}
        
        for game_id in enhanced_df["game_id"].unique():
            # In a real implementation, we would map the game_id to MLB's game_pk
            # For now, we'll use a placeholder approach
            # game_pk = self._get_game_pk_from_id(game_id)
            game_pk = "1"  # Placeholder
            
            if game_pk:
                game_contexts[game_id] = self.get_game_context_factors(game_pk)
        
        # Apply game context to predictions
        for idx, row in enhanced_df.iterrows():
            game_id = row.get("game_id")
            context = game_contexts.get(game_id, {})
            
            if context:
                # Calculate game state adjustment factors
                
                # 1. Pitcher fatigue boosts HR probability
                fatigue_boost = context.get("pitcher_fatigue", 0) * 0.15
                
                # 2. Score differential affects approach
                score_diff = context.get("score_differential", 0)
                score_factor = 0
                
                if score_diff >= 4:
                    # Blowout situation - slight boost as pitchers throw more strikes
                    score_factor = 0.05
                elif score_diff <= 1:
                    # Close game - slight reduction as pitchers are more careful
                    score_factor = -0.02
                
                # 3. Inning progression - late innings might see different pitcher usage
                inning = context.get("inning", 1)
                inning_factor = 0
                
                if inning >= 7:
                    if context.get("starter_replaced", False):
                        # Facing relievers - could be better or worse for HR
                        # Would need to account for bullpen quality
                        inning_factor = 0
                    else:
                        # Tired starter still in - boost
                        inning_factor = 0.08
                
                # Combine all factors
                game_state_adjustment = fatigue_boost + score_factor + inning_factor
                
                # Apply the adjustment to HR_Score
                current_score = enhanced_df.at[idx, "HR_Score"]
                enhanced_df.at[idx, "HR_Score"] = min(1.0, max(0.0, current_score + game_state_adjustment))
                
                # Add the game context data to the DataFrame
                for key, value in context.items():
                    col_name = f"game_{key}"
                    enhanced_df.at[idx, col_name] = value
        
        return enhanced_df

def apply_game_state_factors(predictions_df):
    """
    Convenience function to apply game state factors to predictions.
    
    Args:
        predictions_df (pandas.DataFrame): DataFrame with baseline predictions
        
    Returns:
        pandas.DataFrame: Enhanced predictions with game state factors
    """
    monitor = GameStateMonitor()
    return monitor.enhance_predictions_with_game_state(predictions_df)
