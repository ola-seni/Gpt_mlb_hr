#!/usr/bin/env python3
"""
Test script to verify the fixes to the MLB HR prediction system
"""

import os
import sys
import pandas as pd
import time
from datetime import datetime

def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("MLB HR PREDICTION SYSTEM - TEST SCRIPT")
    print("=" * 60)
    
    # Step 1: Clear all cache to ensure fresh data
    print("\n🧹 Clearing cache data...")
    os.system("rm -rf cache/*")
    print("✅ Cache cleared")
    
    # Step 2: Run the main script in test mode with debug output
    print("\n🧪 Running main.py in test mode...")
    start_time = time.time()
    os.system("python main.py --test --debug > test_output.log 2>&1")
    end_time = time.time()
    print(f"✅ Test run completed in {end_time - start_time:.2f} seconds")
    
    # Step 3: Analyze the output
    print("\n📊 Analyzing results...")
    
    # Check if the output file exists
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = f"results/hr_predictions_{today}.csv"
    
    if not os.path.exists(output_file):
        print("❌ No output file generated!")
        return False
    
    # Read the output file
    df = pd.read_csv(output_file)
    
    print(f"✅ Output file found with {len(df)} predictions")
    
    # Check for variety in the predictions
    unique_batters = df['batter_name'].nunique()
    print(f"📊 Number of unique batters: {unique_batters}")
    
    # Check if we're still getting the same 4 players
    if unique_batters <= 4:
        print("❌ Still getting a limited set of players - check logs for details")
        
        # Show what players we got
        print("\nCurrent player predictions:")
        for batter in df['batter_name'].unique():
            print(f"- {batter}")
    else:
        print("✅ Getting a good variety of players!")
        
        # Show top 10 predictions
        print("\nTop 10 HR predictions:")
        top_10 = df.sort_values('matchup_score', ascending=False).head(10)
        for _, row in top_10.iterrows():
            print(f"- {row['batter_name']} vs {row['opposing_pitcher']} ({row['matchup_score']:.3f})")
    
    # Check if ballpark info is present
    if 'ballpark' in df.columns and not df['ballpark'].isnull().any():
        print("✅ Ballpark data preserved correctly")
    else:
        print("❌ Ballpark data missing or incomplete")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
