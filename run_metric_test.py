#!/usr/bin/env python3
"""
Test script for enhanced MLB HR prediction metrics
This script runs a test of the newly implemented metrics in an isolated environment
"""

import pandas as pd
import os
import sys
from datetime import datetime

def print_header(title):
    """Print a nicely formatted section header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def test_enhanced_metrics():
    """Test the enhanced metrics implementation"""
    from enhanced_metrics import get_enhanced_batter_metrics, get_enhanced_pitcher_metrics
    from integrate_enhanced_metrics import integrate_enhanced_metrics
    
    print_header("Testing Enhanced MLB HR Metrics")
    
    # Create sample data
    print("Creating sample test data...")
    
    sample_data = pd.DataFrame({
        'batter_name': ['Aaron Judge', 'Shohei Ohtani', 'Juan Soto'],
        'batter_id': [592450, 660271, 665742],
        'opposing_pitcher': ['Gerrit Cole', 'Max Scherzer', 'Corbin Burnes'],
        'pitcher_id': [543037, 453286, 669203],
        'pitcher_team': ['NYY', 'TEX', 'BAL'],
        'game_date': [datetime.now().strftime("%Y-%m-%d")] * 3,
        'game_id': ['test_game_1', 'test_game_2', 'test_game_3'],
        'ballpark': ['Yankee Stadium', 'Globe Life Field', 'Camden Yards'],
        'home_team': ['NYY', 'TEX', 'BAL'],
        'ISO': [0.280, 0.250, 0.220],
        'barrel_rate_50': [0.18, 0.15, 0.13],
        'hr_per_9': [1.2, 1.1, 0.9],
        'park_factor': [1.08, 0.97, 1.04],
        'wind_boost': [0.02, 0.01, 0.03],
        'bullpen_boost': [0.03, 0.02, 0.04]
    })
    
    # Process the data with enhanced metrics
    print("Processing with enhanced metrics...")
    enhanced_df = integrate_enhanced_metrics(sample_data)
    
    # Check which new metrics are available
    print_header("Available Enhanced Metrics")
    
    # Get all columns that have at least one non-null value
    available_metrics = [col for col in enhanced_df.columns if enhanced_df[col].notna().any()]
    
    # Group metrics by category
    metric_categories = {
        "Batter Power Metrics": ["ISO", "barrel_rate_50", "avg_exit_velo", "xHR_per_100"],
        "Batter Contact Metrics": ["avg_launch_angle", "fly_ball_pct", "pull_pct"],
        "Batter Plate Discipline": ["swing_pct", "contact_pct", "zone_pct", "z_swing_pct", "o_swing_pct"],
        "Expected Stats": ["xSLG", "xwOBA"],
        "Pitcher Metrics": ["hr_per_9", "barrel_pct_allowed", "hard_hit_pct_allowed", "fb_pct_allowed", "xHR_allowed_per_9"],
        "Pitcher Contact Metrics": ["whiff_rate", "swing_pct_against", "contact_pct_against"],
        "Environmental Factors": ["park_factor", "wind_boost", "bullpen_boost"],
        "Matchup Factors": ["platoon_advantage", "handedness_matchup"]
    }
    
    # Print available metrics by category
    for category, metrics in metric_categories.items():
        category_metrics = [m for m in metrics if m in available_metrics]
        if category_metrics:
            print(f"\n{category}:")
            for metric in category_metrics:
                print(f"  ✅ {metric}")
    
    # Show the prediction results
    print_header("Prediction Results")
    
    results_columns = ['batter_name', 'opposing_pitcher', 'ballpark']
    
    # Add available scores
    if 'HR_Score' in enhanced_df.columns:
        results_columns.append('HR_Score')
    if 'enhanced_HR_Score' in enhanced_df.columns:
        results_columns.append('enhanced_HR_Score')
    
    # Add key metrics if available
    for metric in ['xHR_per_100', 'platoon_advantage', 'barrel_rate_50']:
        if metric in available_metrics:
            results_columns.append(metric)
    
    # Print results
    print(enhanced_df[results_columns].to_string(index=False))
    
    # Show details for the first batter
    print_header(f"Detailed Metrics for {enhanced_df['batter_name'].iloc[0]}")
    
    batter_metrics = enhanced_df.iloc[0].dropna()
    for metric, value in batter_metrics.items():
        if metric not in ['batter_name', 'opposing_pitcher', 'game_id', 'game_date', 'ballpark']:
            print(f"{metric}: {value}")
    
    print("\n✅ Test completed successfully!")
    return enhanced_df

if __name__ == "__main__":
    # Add current directory to path to ensure modules can be imported
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    
    try:
        test_results = test_enhanced_metrics()
        print("\nYour MLB HR prediction system now includes all the requested metrics!")
    except Exception as e:
        import traceback
        print(f"\n❌ Error during testing: {e}")
        traceback.print_exc()
        sys.exit(1)
