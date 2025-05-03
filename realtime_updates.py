# realtime_updates.py
import pandas as pd
import time
import threading
import os
from datetime import datetime
import logging
from lineup_parser import get_confirmed_lineups
from weather import fetch_weather_data, apply_enhanced_weather_boosts
from predictor import generate_enhanced_hr_predictions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/realtime_updates.log',
    filemode='a'
)
logger = logging.getLogger("realtime_updates")

class RealtimeUpdater:
    """
    Class to handle real-time updates to predictions based on:
    - Lineup changes
    - Weather changes
    - Game state (pre-game vs in-game)
    """
    def __init__(self, update_interval=15, in_game_mode=False):
        """
        Initialize the real-time updater.
        
        Args:
            update_interval (int): Minutes between updates
            in_game_mode (bool): Whether to use in-game mode for predictions
        """
        self.update_interval = update_interval 
        self.in_game_mode = in_game_mode
        self.last_predictions = None
        self.running = False
        self.update_thread = None
        self.changes = {
            "lineup": False,
            "weather": False,
            "game_state": False
        }
        
        # Create directory for storing updates
        os.makedirs("results/updates", exist_ok=True)
        
    def start(self):
        """Start the real-time update thread"""
        if self.running:
            logger.warning("Real-time updater already running")
            return
            
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        logger.info(f"Started real-time updater (interval: {self.update_interval} minutes)")
        
    def stop(self):
        """Stop the real-time update thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        logger.info("Stopped real-time updater")
        
    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                self._check_for_updates()
                
                # If any changes detected, regenerate predictions
                if any(self.changes.values()):
                    logger.info(f"Changes detected: {', '.join(k for k, v in self.changes.items() if v)}")
                    self._regenerate_predictions()
                    # Reset change flags
                    self.changes = {k: False for k in self.changes}
                
                # Sleep until next update interval
                for _ in range(self.update_interval * 60):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _check_for_updates(self):
        """Check for updates to lineups, weather, and game state"""
        # Check for lineup changes
        try:
            current_lineups = get_confirmed_lineups()
            
            if self.last_predictions is not None:
                # Compare lineup players to detect changes
                current_players = set(current_lineups['batter_name'].tolist())
                previous_players = set(self.last_predictions['batter_name'].tolist())
                
                if current_players != previous_players:
                    logger.info(f"Lineup changes detected: {len(current_players - previous_players)} new, "
                               f"{len(previous_players - current_players)} removed")
                    self.changes["lineup"] = True
        except Exception as e:
            logger.error(f"Error checking lineup updates: {e}")
        
        # Check for weather changes (every other update to reduce API calls)
        if self.last_predictions is not None and round(time.time()) % (self.update_interval * 120) < 60:
            try:
                # Get sample of locations to check
                locations_to_check = []
                for idx, row in self.last_predictions.sample(min(3, len(self.last_predictions))).iterrows():
                    home_team = row.get('home_team')
                    if home_team:
                        from weather import get_ballpark_locations
                        location = get_ballpark_locations().get(home_team.upper())
                        if location and location not in locations_to_check:
                            locations_to_check.append(location)
                
                # Check weather at these locations
                for location in locations_to_check:
                    weather_data = fetch_weather_data(location)
                    # This will automatically update the cache if changed
                
                self.changes["weather"] = True  # Simplification: always re-apply weather for now
                
            except Exception as e:
                logger.error(f"Error checking weather updates: {e}")
        
        # Check for game state changes (pre-game vs in-game)
        if self.in_game_mode:
            try:
                # Here we would check MLB API for game state changes
                # For now, just log that we're monitoring in-game
                logger.info("Checking for in-game state changes")
                # self.changes["game_state"] = True  # Uncomment when implemented
            except Exception as e:
                logger.error(f"Error checking game state updates: {e}")
    
    def _regenerate_predictions(self):
        """Regenerate predictions based on current data"""
        try:
            logger.info("Regenerating predictions...")
            
            # Get current lineups
            lineups = get_confirmed_lineups()
            
            if lineups.empty:
                logger.warning("No lineups available for prediction update")
                return
                
            # Process through normal pipeline
            from main import safe_execution
            batters = safe_execution(lambda: fetch_batter_metrics(lineups), pd.DataFrame(), 
                                    "Failed to fetch batter metrics")
            pitchers = safe_execution(lambda: fetch_pitcher_metrics(lineups), pd.DataFrame(),
                                     "Failed to fetch pitcher metrics")
            
            if batters.empty or pitchers.empty:
                logger.warning("Missing batter or pitcher data for prediction update")
                return
                
            # Merge data
            merged = pd.merge(batters, pitchers, on="game_id", how="inner")
            
            # Handle opposing_pitcher preservation
            if "opposing_pitcher" in batters.columns and "opposing_pitcher" not in merged.columns:
                merged["opposing_pitcher"] = batters["opposing_pitcher"]
            
            # Add enhanced metrics
            from main import enhance_batter_data
            merged = enhance_batter_data(merged)
            
            # Generate predictions
            predictions = generate_enhanced_hr_predictions(merged)
            
            # Apply weather boosts
            predictions = apply_enhanced_weather_boosts(predictions)
            
            # If we're in in-game mode, apply additional in-game factors
            if self.in_game_mode:
                predictions = self._apply_in_game_factors(predictions)
            
            # Calculate final matchup score
            from main import calculate_enhanced_matchup_score
            predictions["matchup_score"] = predictions.apply(
                calculate_enhanced_matchup_score, axis=1
            )
            
            # Save the updated predictions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = f"results/updates/hr_predictions_update_{timestamp}.csv"
            predictions.to_csv(out_path, index=False)
            
            # Update stored predictions
            self.last_predictions = predictions
            
            logger.info(f"✅ Updated predictions saved to {out_path}")
            
            # Also update the main prediction file
            today = datetime.now().strftime("%Y-%m-%d")
            main_path = f"results/hr_predictions_{today}.csv"
            predictions.to_csv(main_path, index=False)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error regenerating predictions: {e}")
            return None
    
    def _apply_in_game_factors(self, predictions):
        """Apply in-game factors to predictions"""
        logger.info("Applying in-game factors to predictions")
        
        # In-game factors could include:
        # - Pitcher fatigue (pitch count)
        # - Bullpen status
        # - Game score situation
        # - Weather changes during the game
        
        # This is a simplified implementation
        # In a complete implementation, we would fetch current game data from MLB API
        
        try:
            # Apply pitch count factor (simplified example)
            predictions["pitch_count_factor"] = 1.0  # Default
            
            # Apply score situation factor (simplified example)
            predictions["game_situation_factor"] = 1.0  # Default
            
            # Apply bullpen status (simplified example)
            predictions["bullpen_status_factor"] = 1.0  # Default
            
            # Combine these into an in-game boost
            predictions["in_game_boost"] = (
                predictions["pitch_count_factor"] * 0.4 +
                predictions["game_situation_factor"] * 0.3 +
                predictions["bullpen_status_factor"] * 0.3
            )
            
            # Adjust HR_Score with in-game boost
            predictions["HR_Score"] = predictions["HR_Score"] * predictions["in_game_boost"]
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error applying in-game factors: {e}")
            return predictions

# Import these here to avoid circular imports
from fetch_statcast_data import fetch_batter_metrics, fetch_pitcher_metrics

def start_realtime_updates(interval=15, in_game_mode=False):
    """
    Start real-time updates with the specified interval.
    
    Args:
        interval (int): Minutes between updates
        in_game_mode (bool): Whether to use in-game mode
        
    Returns:
        RealtimeUpdater: The updater instance
    """
    updater = RealtimeUpdater(update_interval=interval, in_game_mode=in_game_mode)
    updater.start()
    return updater
