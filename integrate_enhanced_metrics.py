# integrate_enhanced_metrics.py
import pandas as pd
from enhanced_metrics import enhance_matchup_data
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integration")

def integrate_enhanced_metrics(pred_system_df):
    """
    Integrate enhanced metrics into the prediction system DataFrame.
    
    Args:
        pred_system_df (pandas.DataFrame): Original prediction system DataFrame
        
    Returns:
        pandas.DataFrame: Enhanced DataFrame with additional metrics
    """
    logger.info("Integrating enhanced metrics into prediction system")
    
    try:
        # Add enhanced metrics
        enhanced_df = enhance_matchup_data(pred_system_df.copy())
        
        # Update prediction formula to incorporate new metrics
        logger.info("Updating prediction formula with enhanced metrics")
        
        # Only make changes if we actually have the new data
        has_enhanced_data = (
            enhanced_df['avg_exit_velo'].notna().any() or
            enhanced_df['xSLG'].notna().any() or
            enhanced_df['platoon_advantage'].notna().any() or
            enhanced_df['xHR_per_100'].notna().any() or  # Check for new metric
            enhanced_df['swing_pct'].notna().any()       # Check for new metric
        )
        
        if has_enhanced_data:
            enhanced_df['enhanced_HR_Score'] = calculate_enhanced_hr_score(enhanced_df)
            logger.info("Successfully added enhanced HR score")
        else:
            logger.warning("Enhanced metrics not available, keeping original HR_Score")
            
        return enhanced_df
        
    except Exception as e:
        logger.error(f"Error integrating enhanced metrics: {e}")
        return pred_system_df

def calculate_enhanced_hr_score(df):
    """
    Calculate an enhanced HR score using all available metrics including newly added ones.
    
    Args:
        df (pandas.DataFrame): DataFrame with enhanced metrics
        
    Returns:
        pandas.Series: Series with enhanced HR scores
    """
    # Start with base calculations similar to the original system
    base_score = (
        df['ISO'].fillna(0) * 0.25 +
        df['barrel_rate_50'].fillna(0) * 0.20
    )
    
    # Add new components if available
    new_components = pd.Series(0, index=df.index)
    
    # Exit velocity contribution
    if df['avg_exit_velo'].notna().any():
        # Normalize EV: 85 mph = 0, 95 mph = 0.1
        new_components += df['avg_exit_velo'].apply(
            lambda x: max(0, min(0.1, (x - 85) / 100)) if pd.notna(x) else 0
        )
    
    # Launch angle contribution - optimal is around 25-30 degrees
    if df['avg_launch_angle'].notna().any():
        new_components += df['avg_launch_angle'].apply(
            lambda x: max(0, 0.07 - abs(x - 27.5) * 0.01) if pd.notna(x) else 0
        )
    
    # Pull percentage contribution
    if df['pull_pct'].notna().any():
        new_components += df['pull_pct'].apply(
            lambda x: x * 0.05 if pd.notna(x) else 0
        )
    
    # Fly ball percentage contribution
    if df['fb_pct_allowed'].notna().any() and df['fly_ball_pct'].notna().any():
        # Batter who hits fly balls against pitcher who allows fly balls
        new_components += df.apply(
            lambda x: min(x['fly_ball_pct'], x['fb_pct_allowed']) * 0.05 
            if pd.notna(x['fly_ball_pct']) and pd.notna(x['fb_pct_allowed']) else 0,
            axis=1
        )
    
    # xSLG contribution
    if df['xSLG'].notna().any():
        new_components += df['xSLG'].apply(
            lambda x: x * 0.1 if pd.notna(x) else 0
        )
        
    # Recent HR contribution
    if df['hrs_last_10_games'].notna().any():
        new_components += df['hrs_last_10_games'].apply(
            lambda x: min(x * 0.02, 0.1) if pd.notna(x) else 0
        )
    
    # Platoon advantage
    if df['platoon_advantage'].notna().any():
        new_components += df['platoon_advantage'].apply(
            lambda x: (x - 0.5) * 0.1 if pd.notna(x) else 0
        )
    
    # NEW: xHR contribution (expected home runs)
    if df['xHR_per_100'].notna().any():
        new_components += df['xHR_per_100'].apply(
            lambda x: min(x * 0.015, 0.15) if pd.notna(x) else 0  # Scale appropriately
        )
    
    # NEW: Plate discipline metrics
    # Positive factors: good contact rate, good zone judgment
    if df['contact_pct'].notna().any() and df['swing_pct'].notna().any():
        new_components += df.apply(
            lambda x: (
                (x['contact_pct'] - 0.7) * 0.1 +  # Bonus for high contact
                (x['swing_pct'] - 0.5) * 0.05     # Moderate bonus for selective swinging
            ) if pd.notna(x['contact_pct']) and pd.notna(x['swing_pct']) else 0,
            axis=1
        )
    
    # NEW: Zone discipline (bonus for batters who lay off bad pitches)
    if df['z_swing_pct'].notna().any() and df['o_swing_pct'].notna().any():
        new_components += df.apply(
            lambda x: (
                (x['z_swing_pct'] - x['o_swing_pct']) * 0.05  # Reward good zone judgment
            ) if pd.notna(x['z_swing_pct']) and pd.notna(x['o_swing_pct']) else 0,
            axis=1
        )
    
    # Pitcher factors
    pitcher_factor = (
        df['hr_per_9'].fillna(0) * 0.03  # Higher HR/9 increases batter chance
    )
    
    if df['barrel_pct_allowed'].notna().any():
        pitcher_factor += df['barrel_pct_allowed'].apply(
            lambda x: x * 0.15 if pd.notna(x) else 0
        )
    
    if df['hard_hit_pct_allowed'].notna().any():
        pitcher_factor += df['hard_hit_pct_allowed'].apply(
            lambda x: x * 0.1 if pd.notna(x) else 0
        )
    
    # NEW: Expected HRs allowed by pitcher
    if df['xHR_allowed_per_9'].notna().any():
        pitcher_factor += df['xHR_allowed_per_9'].apply(
            lambda x: x * 0.02 if pd.notna(x) else 0
        )
    
    # NEW: Pitcher whiff rate (negative factor - higher whiff rate decreases HR chance)
    if df['whiff_rate'].notna().any():
        pitcher_factor -= df['whiff_rate'].apply(
            lambda x: x * 0.1 if pd.notna(x) else 0
        )
    
    # Environmental factors (from original system)
    env_factor = pd.Series(0, index=df.index)

    # Add park_factor if available
    if 'park_factor' in df.columns:
        env_factor += df['park_factor'].fillna(1.0) * 0.1
    else:
        # Use default park factor
        env_factor += 1.0 * 0.1

    # Add wind_boost if available
    if 'wind_boost' in df.columns:
        env_factor += df['wind_boost'].fillna(0) * 0.1

    # Add bullpen_boost if available
    if 'bullpen_boost' in df.columns:
        env_factor += df['bullpen_boost'].fillna(0) * 0.05
    
    # Combine everything
    enhanced_score = base_score + new_components + pitcher_factor + env_factor
    
    # Normalize to similar range as the original system (0 to 0.8)
    return enhanced_score.clip(0, 0.8)
