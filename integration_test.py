#!/usr/bin/env python3
# integration_test.py - Test all components of the MLB HR prediction system
import os
import sys
import time
from datetime import datetime

def print_header(title):
    """Print a nicely formatted section header"""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

def timestamp():
    """Get current timestamp for logging"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    """Run integration tests for all components"""
    # Set up test environment
    os.environ["TEST_MODE"] = "1"  # Enable test mode
    print_header("MLB HR Prediction System - Integration Test")
    print(f"[{timestamp()}] Starting integration tests...")
    
    # Test component 1: Lineup Parser
    print_header("Testing Lineup Parser")
    try:
        from lineup_parser import get_confirmed_lineups
        lineups = get_confirmed_lineups(force_test=True)
        print(f"✅ Got {len(lineups)} test lineups")
        print(lineups.head(2))
    except Exception as e:
        print(f"❌ Lineup parser test failed: {e}")
        return False
        
    # Test component 2: Statcast Data
    print_header("Testing Statcast Data Fetching")
    try:
        from fetch_statcast_data import fetch_batter_metrics, fetch_pitcher_metrics
        
        print("Testing batter metrics...")
        batters = fetch_batter_metrics(lineups)
        print(f"✅ Got metrics for {len(batters)} batters")
        print(batters.head(2))
        
        print("Testing pitcher metrics...")
        pitchers = fetch_pitcher_metrics(lineups)
        print(f"✅ Got metrics for {len(pitchers)} pitchers")
        print(pitchers.head(2))
    except Exception as e:
        print(f"❌ Statcast data test failed: {e}")
        return False
    
    # Test component 3: Weather Integration
    print_header("Testing Weather API")
    try:
        from weather import fetch_weather_data, get_ballpark_locations
        
        # Test a known location
        location = "New York,US"
        print(f"Testing weather for {location}...")
        weather = fetch_weather_data(location)
        
        if weather:
            print(f"✅ Got weather data: {weather.get('main', {}).get('temp')}°C, "
                  f"wind: {weather.get('wind', {}).get('speed', 0)} m/s")
        else:
            print("⚠️ No weather data returned, but test continues")
            
        # Test ballpark mappings
        locations = get_ballpark_locations()
        print(f"✅ Ballpark locations: {len(locations)} mapped")
    except Exception as e:
        print(f"❌ Weather API test failed: {e}")
        print("⚠️ Continuing with tests...")
    
    # Test component 4: Prediction Engine
    print_header("Testing Prediction Engine")
    try:
        from predictor import generate_enhanced_hr_predictions
        
        # Create a small test DataFrame
        import pandas as pd
        test_data = pd.DataFrame({
            'batter_name': ['Test Batter 1', 'Test Batter 2'],
            'ISO': [0.250, 0.180],
            'barrel_rate_50': [0.15, 0.08],
            'hr_per_9': [1.2, 0.8],
            'pitch_matchup_score': [0.2, 0.1],
            'bullpen_boost': [0.05, 0.02]
        })
        
        predictions = generate_enhanced_hr_predictions(test_data)
        print(f"✅ Generated {len(predictions)} predictions")
        print(predictions)
    except Exception as e:
        print(f"❌ Prediction engine test failed: {e}")
        return False
    
    # Test component 5: Telegram Integration
    print_header("Testing Telegram Integration")
    if os.getenv("BOT_TOKEN") and os.getenv("CHAT_ID"):
        try:
            from telegram_alerts import send_telegram_alerts
            
            # Create a test DataFrame
            import pandas as pd
            test_data = pd.DataFrame({
                'batter_name': ['TEST PLAYER - IGNORE'],
                'opposing_pitcher': ['TEST PITCHER'],
                'HR_Score': [0.5],
                'matchup_score': [0.5],
                'ballpark': ['TEST BALLPARK'],
                'park_factor': [1.05],
                'wind_boost': [0.02],
                'tag': ['TEST 🧪']
            })
            
            print("Sending test message to Telegram...")
            send_telegram_alerts(test_data)
            print("✅ Telegram test message sent")
        except Exception as e:
            print(f"❌ Telegram test failed: {e}")
            print("⚠️ Continuing with tests...")
    else:
        print("⚠️ Skipping Telegram test (missing credentials)")
    
    # Test component 6: Full Integration Test
    print_header("Full Integration Test")
    try:
        import main
        
        print("Running full prediction pipeline in test mode...")
        predictions = main.main()
        
        if predictions is not None and not predictions.empty:
            print(f"✅ Full integration test successful: {len(predictions)} predictions generated")
            print(predictions.head(3))
        else:
            print("⚠️ No predictions generated, but test completed without errors")
    except Exception as e:
        print(f"❌ Full integration test failed: {e}")
        return False
    
    # Success!
    print_header("All Tests Completed")
    print("✅ Integration tests completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
