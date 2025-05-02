# backtest.py
import pandas as pd
import os
from datetime import datetime, timedelta
from predictor import generate_hr_predictions
from weather import apply_weather_boosts, get_park_factor
from pybaseball import statcast_batter, statcast_pitcher, playerid_lookup, statcast
import joblib
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

def run_backtesting(start_date, end_date, output_dir="backtest_results"):
    """
    Run a comprehensive backtesting of the HR prediction system
    against historical data from start_date to end_date.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        output_dir (str): Directory to save results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🔍 Running backtesting from {start_date} to {end_date}")
    
    # Convert to datetime for iteration
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
    
    all_results = []
    
    # Process each day
    while current_date <= end_datetime:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"📅 Processing {date_str}")
        
        try:
            # Get actual games and outcomes for this date
            daily_games = get_historical_games(date_str)
            
            if daily_games.empty:
                print(f"⚠️ No games found for {date_str}")
                current_date += timedelta(days=1)
                continue
            
            # Enrich with player stats up to the day before
            one_day_before = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
            season_start = f"{current_date.year}-03-20"  # Approximate season start
            
            # Get batter and pitcher metrics
            batters_df = get_historical_batter_metrics(
                daily_games["batter_id"].unique().tolist(), 
                season_start, 
                one_day_before
            )
            
            pitchers_df = get_historical_pitcher_metrics(
                daily_games["pitcher_id"].unique().tolist(),
                season_start,
                one_day_before
            )
            
            # Merge data
            merged = pd.merge(
                daily_games, 
                batters_df, 
                on="batter_id", 
                how="left"
            )
            
            merged = pd.merge(
                merged,
                pitchers_df,
                on="pitcher_id",
                how="left"
            )
            
            # Add other features
            merged["pitch_matchup_score"] = np.random.uniform(0.1, 0.2, size=len(merged))  # Simplified for backtest
            merged["bullpen_boost"] = np.random.uniform(0, 0.05, size=len(merged))  # Simplified for backtest
            
            # Apply park factors
            merged["park_factor"] = merged["home_team"].apply(lambda x: get_park_factor(x))
            merged["wind_boost"] = 0  # Simplified as historical weather is harder to get
            
            # Generate predictions
            predictions = generate_hr_predictions(merged)
            
            # Record results
            predictions["actual_date"] = date_str
            all_results.append(predictions)
            
        except Exception as e:
            print(f"❌ Error processing {date_str}: {e}")
        
        current_date += timedelta(days=1)
    
    # Combine all results
    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        
        # Calculate metrics
        calculate_performance_metrics(final_df, output_dir)
        
        # Save results
        results_path = os.path.join(output_dir, f"backtest_{start_date}_to_{end_date}.csv")
        final_df.to_csv(results_path, index=False)
        print(f"✅ Backtesting complete. Results saved to {results_path}")
        return final_df
    else:
        print("❌ No valid results generated during backtesting")
        return pd.DataFrame()

def get_historical_games(date_str):
    """
    Get all MLB games from a specific date with outcomes
    """
    try:
        # Get statcast data for the day
        df = statcast(date_str, date_str)
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter for at-bats only
        df = df[df["events"].notna()]
        
        # Create game and matchup identifiers
        df["game_id"] = df["game_pk"]
        df["matchup_id"] = df["batter"].astype(str) + "_vs_" + df["pitcher"].astype(str)
        
        # Mark home runs
        df["hit_hr"] = df["events"] == "home_run"
        
        # Create a clean dataframe with unique batter-pitcher matchups
        games_df = df.groupby(["matchup_id", "batter", "pitcher", "game_pk", "home_team"]).agg({
            "hit_hr": "max",  # 1 if any HR in matchup, 0 otherwise
            "player_name": "first",  # Batter name
            "pitcher_name": "first",
        }).reset_index()
        
        games_df.rename(columns={
            "batter": "batter_id",
            "pitcher": "pitcher_id",
            "player_name": "batter_name",
        }, inplace=True)
        
        return games_df
    
    except Exception as e:
        print(f"Error fetching historical games: {e}")
        return pd.DataFrame()

def get_historical_batter_metrics(batter_ids, start_date, end_date):
    """Get historical batter metrics up to a specific date"""
    metrics = []
    
    for batter_id in tqdm(batter_ids, desc="Fetching batter metrics"):
        try:
            # Get statcast data
            stats = statcast_batter(start_date, end_date, batter_id)
            
            if stats.empty:
                continue
                
            # Calculate ISO
            batted = stats[stats['events'].notna()]
            if batted.empty:
                continue
                
            iso = (
                batted['events'].eq('double').sum() * 2 +
                batted['events'].eq('triple').sum() * 3 +
                batted['events'].eq('home_run').sum() * 4
            ) / max(1, batted.shape[0])
            
            # Calculate barrel rate
            barrel_events = 0
            if 'launch_speed' in batted.columns and 'launch_angle' in batted.columns:
                barrel_events = (
                    batted['launch_speed'].fillna(0).gt(98) &
                    batted['launch_angle'].fillna(0).between(26, 30)
                ).sum()
                
            barrel_rate = barrel_events / max(1, len(batted))
            
            metrics.append({
                "batter_id": batter_id,
                "ISO": round(iso, 3),
                "barrel_rate_50": round(barrel_rate, 3)
            })
            
        except Exception as e:
            print(f"Error processing batter {batter_id}: {e}")
    
    return pd.DataFrame(metrics)

def get_historical_pitcher_metrics(pitcher_ids, start_date, end_date):
    """Get historical pitcher metrics up to a specific date"""
    metrics = []
    
    for pitcher_id in tqdm(pitcher_ids, desc="Fetching pitcher metrics"):
        try:
            # Get statcast data
            stats = statcast_pitcher(start_date, end_date, pitcher_id)
            
            if stats.empty:
                continue
                
            # Calculate HR/9
            outs = stats['outs_when_up'].fillna(0).sum()
            ip = outs / 3.0
            hr = stats['events'].eq('home_run').sum()
            hr_per_9 = (hr / ip) * 9 if ip > 0 else 0.0
            
            metrics.append({
                "pitcher_id": pitcher_id,
                "hr_per_9": round(hr_per_9, 3)
            })
            
        except Exception as e:
            print(f"Error processing pitcher {pitcher_id}: {e}")
    
    return pd.DataFrame(metrics)

def calculate_performance_metrics(results_df, output_dir):
    """Calculate and save performance metrics"""
    # Set thresholds
    results_df["prediction_tier"] = pd.cut(
        results_df["HR_Score"], 
        bins=[-float('inf'), 0.15, 0.25, float('inf')],
        labels=["Risky", "Sleeper", "Lock"]
    )
    
    # Overall metrics
    try:
        auc = roc_auc_score(results_df["hit_hr"], results_df["HR_Score"])
    except:
        auc = 0
    
    # Metrics by threshold
    metrics = []
    for tier in ["Risky", "Sleeper", "Lock"]:
        tier_df = results_df[results_df["prediction_tier"] == tier]
        if len(tier_df) == 0:
            continue
            
        total = len(tier_df)
        hits = tier_df["hit_hr"].sum()
        hit_rate = hits / total if total > 0 else 0
        
        metrics.append({
            "Tier": tier,
            "Total_Predictions": total,
            "HR_Hits": int(hits),
            "Hit_Rate": hit_rate,
            "Avg_Score": tier_df["HR_Score"].mean()
        })
    
    metrics_df = pd.DataFrame(metrics)
    
    # Save metrics
    metrics_path = os.path.join(output_dir, "performance_metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)
    
    # Create visualization
    plt.figure(figsize=(12, 6))
    
    # Plot hit rate by tier
    plt.subplot(1, 2, 1)
    bars = plt.bar(metrics_df["Tier"], metrics_df["Hit_Rate"] * 100)
    plt.title("HR Hit Rate by Prediction Tier")
    plt.ylabel("Hit Rate (%)")
    plt.ylim(0, max(metrics_df["Hit_Rate"] * 100) * 1.2)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.1f}%',
                 ha='center', va='bottom')
    
    # Plot prediction distribution
    plt.subplot(1, 2, 2)
    plt.hist(results_df["HR_Score"], bins=20)
    plt.axvline(0.15, color='r', linestyle='--', label="Sleeper Threshold")
    plt.axvline(0.25, color='g', linestyle='--', label="Lock Threshold")
    plt.title("Distribution of HR Scores")
    plt.xlabel("HR Score")
    plt.ylabel("Count")
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "performance_summary.png"))
    plt.close()
    
    # Print summary
    print("\n📊 Performance Summary:")
    print(f"AUC Score: {auc:.3f}")
    print(metrics_df.to_string(index=False))
    print(f"\nDetailed metrics saved to {metrics_path}")

if __name__ == "__main__":
    # Example: Run backtesting for the 2023 season (or a portion of it)
    # You can adjust these dates as needed
    results = run_backtesting("2023-05-01", "2023-05-15")
