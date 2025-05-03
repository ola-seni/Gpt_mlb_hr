# test_enhanced_metrics.py
import pandas as pd
from enhanced_metrics import get_enhanced_batter_metrics, get_enhanced_pitcher_metrics
from integrate_enhanced_metrics import integrate_enhanced_metrics
from datetime import datetime, timedelta

def test_enhanced_metrics():
    """Test the enhanced metrics implementation."""
    print("🧪 Testing Enhanced Metrics")
    
    # Test dates
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Test batter (Aaron Judge)
    batter_id = 592450
    print(f"Fetching metrics for Aaron Judge (ID: {batter_id})...")
    batter_metrics = get_enhanced_batter_metrics(batter_id, start_date, end_date)
    print("\n📊 Batter Metrics (Aaron Judge):")
    for key, value in batter_metrics.items():
        print(f"  {key}: {value}")
    
    # Test pitcher (Gerrit Cole)
    pitcher_id = 543037
    print(f"\nFetching metrics for Gerrit Cole (ID: {pitcher_id})...")
    pitcher_metrics = get_enhanced_pitcher_metrics(pitcher_id, start_date, end_date)
    print("\n📊 Pitcher Metrics (Gerrit Cole):")
    for key, value in pitcher_metrics.items():
        if key != 'pitch_mix':
            print(f"  {key}: {value}")
    
    if 'pitch_mix' in pitcher_metrics:
        print("\n🔢 Pitch Mix:")
        for pitch, pct in pitcher_metrics.get('pitch_mix', {}).items():
            print(f"  {pitch}: {pct:.3f}")
    
    # Test integration with sample data
    print("\n🔄 Testing Integration")
    sample_df = pd.DataFrame({
        'batter_id': [592450, 665742],
        'batter_name': ['Aaron Judge', 'Juan Soto'],
        'pitcher_id': [543037, 669203],
        'opposing_pitcher': ['Gerrit Cole', 'Corbin Burnes'],
        'ISO': [0.250, 0.230],
        'barrel_rate_50': [0.15, 0.12],
        'hr_per_9': [0.9, 1.1],
        'park_factor': [1.05, 1.02],
        'wind_boost': [0.02, 0.01],
        'bullpen_boost': [0.03, 0.02]
    })
    
    print("Sample data before enhancement:")
    print(sample_df[['batter_name', 'opposing_pitcher', 'ISO', 'barrel_rate_50']].head())
    
    enhanced_df = integrate_enhanced_metrics(sample_df)
    
    print("\n📈 Original vs Enhanced Scores:")
    for _, row in enhanced_df.iterrows():
        print(f"  {row['batter_name']} vs {row['opposing_pitcher']}:")
        
        if 'enhanced_HR_Score' in enhanced_df.columns:
            # Safely format numeric values
            hr_score = row.get('HR_Score')
            if isinstance(hr_score, (int, float)):
                print(f"    Original: {hr_score:.3f}")
            else:
                print(f"    Original: {hr_score}")
                
            enh_score = row.get('enhanced_HR_Score')
            if isinstance(enh_score, (int, float)):
                print(f"    Enhanced: {enh_score:.3f}")
            else:
                print(f"    Enhanced: {enh_score}")
            
            # Show what's different
            print(f"    New Metrics:")
            for col in ['avg_exit_velo', 'xSLG', 'hrs_last_10_games', 
                      'platoon_advantage', 'barrel_pct_allowed']:
                if col in enhanced_df.columns and pd.notna(row.get(col)):
                    print(f"      {col}: {row.get(col)}")
        else:
            print("    Enhanced metrics not available")
    
    print("\n✅ Test complete")

if __name__ == "__main__":
    test_enhanced_metrics()
