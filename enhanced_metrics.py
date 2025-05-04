# enhanced_metrics.py
import pandas as pd
import numpy as np
from pybaseball import statcast_batter, statcast_pitcher, playerid_lookup
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("enhanced_metrics")

def get_enhanced_batter_metrics(batter_id, start_date, end_date):
    """
    Fetch enhanced batter metrics from Statcast data.
    
    Args:
        batter_id (int): MLB player ID for the batter
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        dict: Dictionary containing enhanced batter metrics
    """
    logger.info(f"Fetching enhanced metrics for batter {batter_id}")
    
    try:
        # Get statcast data
        df = statcast_batter(start_date, end_date, batter_id)
        
        if df.empty:
            logger.warning(f"No data found for batter {batter_id}")
            return {}
            
        # Calculate basic stats
        batted_balls = df[df['description'].isin(['hit_into_play', 'home_run'])]
        
        metrics = {}
        
        # Calculate ISO (standard calculation)
        hits = df[df['events'].notna()]
        singles = hits['events'].eq('single').sum()
        doubles = hits['events'].eq('double').sum()
        triples = hits['events'].eq('triple').sum()
        homers = hits['events'].eq('home_run').sum()
        at_bats = len(hits)
        
        # ISO = (2B + 2*3B + 3*HR) / AB
        iso = (doubles + 2*triples + 3*homers) / max(1, at_bats)
        metrics['ISO'] = round(iso, 3)
        
        # Calculate Barrel %
        if 'launch_speed' in batted_balls.columns and 'launch_angle' in batted_balls.columns:
            # Statcast barrel definition: >=98 mph EV and 26-30 degree launch angle
            barrels = batted_balls[
                (batted_balls['launch_speed'] >= 98) & 
                (batted_balls['launch_angle'].between(26, 30))
            ]
            barrel_pct = len(barrels) / max(1, len(batted_balls))
            metrics['barrel_rate'] = round(barrel_pct, 3)
        
        # Average Exit Velocity
        if 'launch_speed' in batted_balls.columns:
            avg_ev = batted_balls['launch_speed'].mean()
            metrics['avg_exit_velo'] = round(avg_ev, 1) if not pd.isna(avg_ev) else None
        
        # Average Launch Angle
        if 'launch_angle' in batted_balls.columns:
            avg_la = batted_balls['launch_angle'].mean()
            metrics['avg_launch_angle'] = round(avg_la, 1) if not pd.isna(avg_la) else None
        
        # Fly Ball %
        if 'bb_type' in batted_balls.columns:
            fly_balls = batted_balls[batted_balls['bb_type'] == 'fly_ball']
            fb_pct = len(fly_balls) / max(1, len(batted_balls))
            metrics['fly_ball_pct'] = round(fb_pct, 3)
        
        # Pull %
        if 'hit_location' in batted_balls.columns and 'stand' in batted_balls.columns:
            # For RHB: Pull = 7,8,9 (left field) | For LHB: Pull = 3,4,5 (right field)
            righty_pull = batted_balls[
                (batted_balls['stand'] == 'R') & 
                (batted_balls['hit_location'].isin([7, 8, 9]))
            ]
            
            lefty_pull = batted_balls[
                (batted_balls['stand'] == 'L') & 
                (batted_balls['hit_location'].isin([3, 4, 5]))
            ]
            
            pull_count = len(righty_pull) + len(lefty_pull)
            pull_pct = pull_count / max(1, len(batted_balls))
            metrics['pull_pct'] = round(pull_pct, 3)
        
        # xSLG
        if 'estimated_ba_using_speedangle' in batted_balls.columns and 'estimated_slg_using_speedangle' in batted_balls.columns:
            # Use Statcast's expected stats
            xslg_values = batted_balls['estimated_slg_using_speedangle'].dropna()
            if not xslg_values.empty:
                metrics['xSLG'] = round(xslg_values.mean(), 3)
        
        # xwOBA
        if 'estimated_woba_using_speedangle' in batted_balls.columns:
            xwoba_values = batted_balls['estimated_woba_using_speedangle'].dropna()
            if not xwoba_values.empty:
                metrics['xwOBA'] = round(xwoba_values.mean(), 3)
        
        # HRs in last 10 games
        if 'game_date' in df.columns:
            df['game_date'] = pd.to_datetime(df['game_date'])
            # Sort by date
            sorted_df = df.sort_values('game_date', ascending=False)
            # Get unique game dates
            unique_games = sorted_df['game_date'].dt.date.unique()
            # Take the 10 most recent games (or fewer if there are less than 10)
            recent_games = unique_games[:min(10, len(unique_games))]
            # Count HRs in these games
            recent_hrs = sorted_df[
                sorted_df['game_date'].dt.date.isin(recent_games) &
                sorted_df['events'].eq('home_run')
            ].shape[0]
            metrics['hrs_last_10_games'] = recent_hrs
        
        # Handedness
        if 'stand' in df.columns:
            # Get the most common stance
            stands = df['stand'].value_counts()
            if not stands.empty:
                metrics['batter_handedness'] = stands.index[0]
                
        # NEW: Expected Home Runs (xHR)
        # Calculate based on exit velocity, launch angle, and barrel rate
        if 'launch_speed' in batted_balls.columns and 'launch_angle' in batted_balls.columns:
            # Identify optimal launch conditions for HRs (95+ mph, 25-35 degrees)
            optimal_hits = batted_balls[
                (batted_balls['launch_speed'] >= 95) &
                (batted_balls['launch_angle'].between(25, 35))
            ]
            
            # Calculate expected HR per batted ball based on optimal conditions
            batted_ball_count = len(batted_balls)
            optimal_count = len(optimal_hits)
            
            if batted_ball_count > 0:
                # HR probability increases with higher percentages of optimal hits
                optimal_pct = optimal_count / batted_ball_count
                
                # Calculate expected HR rate (normalized)
                xHR_rate = optimal_pct * 0.5  # Scale factor
                
                # Scale by overall batted ball quality
                if 'avg_exit_velo' in metrics and metrics['avg_exit_velo'] is not None:
                    ev_factor = min(1.5, max(0.5, metrics['avg_exit_velo'] / 90))
                    xHR_rate *= ev_factor
                
                # Calculate expected HRs per 100 at bats
                metrics['xHR_per_100'] = round(xHR_rate * 100, 1)
        
        # NEW: Plate Discipline Metrics
        if 'description' in df.columns:
            # Total pitches
            total_pitches = len(df)
            
            # Swings (all types of swings)
            swings = df['description'].str.contains('swing').sum() + df['description'].eq('hit_into_play').sum() + df['description'].eq('home_run').sum()
            
            # Contacts (all types of contact)
            contacts = df['description'].isin(['foul', 'hit_into_play', 'home_run', 'foul_tip']).sum()
            
            # Pitches in zone (approximation)
            zone_pitches = df['zone'].between(1, 9).sum() if 'zone' in df.columns else 0
            
            # Calculate plate discipline metrics
            if total_pitches > 0:
                metrics['swing_pct'] = round(swings / total_pitches, 3)
                
                if swings > 0:
                    metrics['contact_pct'] = round(contacts / swings, 3)
                
                if 'zone' in df.columns:
                    metrics['zone_pct'] = round(zone_pitches / total_pitches, 3)
                    
                    # Calculate swing rates for pitches in/out of zone
                    zone_df = df[df['zone'].between(1, 9)]
                    outside_df = df[~df['zone'].between(1, 9)]
                    
                    zone_swings = zone_df['description'].str.contains('swing').sum() + zone_df['description'].eq('hit_into_play').sum()
                    outside_swings = outside_df['description'].str.contains('swing').sum() + outside_df['description'].eq('hit_into_play').sum()
                    
                    if len(zone_df) > 0:
                        metrics['z_swing_pct'] = round(zone_swings / len(zone_df), 3)
                    
                    if len(outside_df) > 0:
                        metrics['o_swing_pct'] = round(outside_swings / len(outside_df), 3)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error fetching enhanced batter metrics: {e}")
        return {}

def get_enhanced_pitcher_metrics(pitcher_id, start_date, end_date):
    """
    Fetch enhanced pitcher metrics from Statcast data.
    
    Args:
        pitcher_id (int): MLB player ID for the pitcher
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        dict: Dictionary containing enhanced pitcher metrics
    """
    logger.info(f"Fetching enhanced metrics for pitcher {pitcher_id}")
    
    try:
        # Get statcast data
        df = statcast_pitcher(start_date, end_date, pitcher_id)
        
        if df.empty:
            logger.warning(f"No data found for pitcher {pitcher_id}")
            return {}
            
        metrics = {}
        
        # Calculate HR/9
        outs = df['outs_when_up'].fillna(0).sum()
        ip = outs / 3.0
        hr = df['events'].eq('home_run').sum()
        hr_per_9 = (hr / ip) * 9 if ip > 0 else 0.0
        metrics['hr_per_9'] = round(hr_per_9, 3)
        
        # Calculate Barrel % allowed
        batted_balls = df[df['type'] == 'X']  # Balls in play
        if 'launch_speed' in batted_balls.columns and 'launch_angle' in batted_balls.columns:
            barrels = batted_balls[
                (batted_balls['launch_speed'] >= 98) & 
                (batted_balls['launch_angle'].between(26, 30))
            ]
            barrel_pct = len(barrels) / max(1, len(batted_balls))
            metrics['barrel_pct_allowed'] = round(barrel_pct, 3)
        
        # Hard Hit % allowed
        if 'launch_speed' in batted_balls.columns:
            hard_hits = batted_balls[batted_balls['launch_speed'] >= 95]
            hard_hit_pct = len(hard_hits) / max(1, len(batted_balls))
            metrics['hard_hit_pct_allowed'] = round(hard_hit_pct, 3)
        
        # FB% allowed
        if 'bb_type' in batted_balls.columns:
            fly_balls = batted_balls[batted_balls['bb_type'] == 'fly_ball']
            fb_pct = len(fly_balls) / max(1, len(batted_balls))
            metrics['fb_pct_allowed'] = round(fb_pct, 3)
        
        # ISO Allowed
        hits = df[df['events'].notna()]
        singles = hits['events'].eq('single').sum()
        doubles = hits['events'].eq('double').sum()
        triples = hits['events'].eq('triple').sum()
        homers = hits['events'].eq('home_run').sum()
        at_bats = len(hits)
        
        iso_allowed = (doubles + 2*triples + 3*homers) / max(1, at_bats)
        metrics['iso_allowed'] = round(iso_allowed, 3)
        
        # Pitch Mix
        pitch_counts = df['pitch_type'].value_counts(normalize=True).to_dict()
        metrics['pitch_mix'] = {k: round(v, 3) for k, v in pitch_counts.items()}
        
        # Pitcher Handedness
        if 'p_throws' in df.columns:
            handedness = df['p_throws'].iloc[0] if not df.empty else None
            if handedness:
                metrics['pitcher_handedness'] = handedness
                
        # NEW: xHR_allowed (Expected HRs allowed)
        if 'launch_speed' in batted_balls.columns and 'launch_angle' in batted_balls.columns:
            # Identify batted balls with HR potential
            hr_potential = batted_balls[
                (batted_balls['launch_speed'] >= 95) &
                (batted_balls['launch_angle'].between(25, 35))
            ]
            
            # Calculate expected HR rate per batted ball
            if len(batted_balls) > 0:
                xHR_allowed_rate = len(hr_potential) / len(batted_balls)
                # Calculate expected HRs allowed per 9 innings
                if ip > 0:
                    metrics['xHR_allowed_per_9'] = round((xHR_allowed_rate * (batted_balls.shape[0] / ip) * 9), 3)
        
        # NEW: Plate Discipline Metrics
        if 'description' in df.columns:
            # Total pitches
            total_pitches = len(df)
            
            # Swings
            swings = df['description'].str.contains('swing').sum() + df['description'].eq('hit_into_play').sum()
            
            # Contacts
            contacts = df['description'].isin(['foul', 'hit_into_play', 'home_run', 'foul_tip']).sum()
            
            # Pitches in zone
            zone_pitches = df['zone'].between(1, 9).sum() if 'zone' in df.columns else 0
            
            # Calculate metrics
            if total_pitches > 0:
                metrics['swing_pct_against'] = round(swings / total_pitches, 3)
                
                if 'zone' in df.columns:
                    metrics['zone_pct'] = round(zone_pitches / total_pitches, 3)
                
                if swings > 0:
                    metrics['contact_pct_against'] = round(contacts / swings, 3)
                    
                # Calculate whiff rate (swings and misses / total swings)
                whiffs = df['description'].eq('swinging_strike').sum()
                if swings > 0:
                    metrics['whiff_rate'] = round(whiffs / swings, 3)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error fetching enhanced pitcher metrics: {e}")
        return {}

def determine_platoon_advantage(batter_handedness, pitcher_handedness):
    """
    Determine platoon advantage for batter vs pitcher matchup.
    
    Args:
        batter_handedness (str): 'L' for left, 'R' for right, 'S' for switch
        pitcher_handedness (str): 'L' for left, 'R' for right
        
    Returns:
        float: Platoon advantage score between 0-1
    """
    # Switch hitters always get advantage against appropriate side
    if batter_handedness == 'S':
        return 0.8  # High advantage but not perfect
    
    # Classic platoon advantages
    if batter_handedness == 'L' and pitcher_handedness == 'R':
        return 0.6  # LHB has advantage vs RHP
    
    if batter_handedness == 'R' and pitcher_handedness == 'L':
        return 0.7  # RHB has bigger advantage vs LHP
    
    # Same handed (disadvantage)
    return 0.4

def enhance_matchup_data(df):
    """
    Enhance a DataFrame of batter-pitcher matchups with advanced metrics.
    
    Args:
        df (pandas.DataFrame): DataFrame containing matchup data
        
    Returns:
        pandas.DataFrame: Enhanced DataFrame with additional metrics
    """
    today = datetime.now().strftime("%Y-%m-%d")
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Create new columns for enhanced metrics
    new_columns = [
        'avg_exit_velo', 'avg_launch_angle', 'fly_ball_pct', 'pull_pct',
        'xSLG', 'xwOBA', 'hrs_last_10_games', 'batter_handedness',
        'barrel_pct_allowed', 'hard_hit_pct_allowed', 'fb_pct_allowed',
        'iso_allowed', 'pitcher_handedness', 'platoon_advantage',
        # New columns
        'xHR_per_100', 'swing_pct', 'contact_pct', 'zone_pct',
        'z_swing_pct', 'o_swing_pct', 'xHR_allowed_per_9',
        'swing_pct_against', 'contact_pct_against', 'whiff_rate'
    ]
    
    for col in new_columns:
        df[col] = None
    
    # Process each matchup
    for idx, row in df.iterrows():
        batter_id = row.get('batter_id')
        pitcher_id = row.get('pitcher_id')
        
        if batter_id and pitcher_id:
            try:
                # Get enhanced batter metrics
                batter_metrics = get_enhanced_batter_metrics(batter_id, one_month_ago, today)
                
                # Get enhanced pitcher metrics
                pitcher_metrics = get_enhanced_pitcher_metrics(pitcher_id, one_month_ago, today)
                
                # Use fallback data if no data is found
                if not batter_metrics:
                    logger.warning(f"Using fallback data for batter {batter_id}")
                    batter_metrics = {
                        'ISO': 0.150,
                        'barrel_rate': 0.08,
                        'avg_exit_velo': 88.5,
                        'avg_launch_angle': 12.5,
                        'batter_handedness': 'R',
                        'xHR_per_100': 3.5,  # New fallback
                        'swing_pct': 0.46,    # New fallback
                        'contact_pct': 0.78   # New fallback
                    }
                
                if not pitcher_metrics:
                    logger.warning(f"Using fallback data for pitcher {pitcher_id}")
                    pitcher_metrics = {
                        'hr_per_9': 1.1,
                        'barrel_pct_allowed': 0.07,
                        'hard_hit_pct_allowed': 0.35,
                        'pitcher_handedness': 'R',
                        'xHR_allowed_per_9': 1.0,  # New fallback
                        'whiff_rate': 0.23         # New fallback
                    }
                
                # Update the DataFrame with new metrics
                for metric, value in batter_metrics.items():
                    if metric in df.columns:
                        df.at[idx, metric] = value
                
                for metric, value in pitcher_metrics.items():
                    if metric in df.columns and metric != 'pitch_mix':
                        df.at[idx, metric] = value
                
                # Calculate platoon advantage if we have handedness data
                batter_hand = batter_metrics.get('batter_handedness')
                pitcher_hand = pitcher_metrics.get('pitcher_handedness')
                
                if batter_hand and pitcher_hand:
                    df.at[idx, 'platoon_advantage'] = determine_platoon_advantage(batter_hand, pitcher_hand)
                    
                    # Add textual description of the matchup
                    matchup_desc = f"{batter_hand}HB vs {pitcher_hand}HP"
                    df.at[idx, 'handedness_matchup'] = matchup_desc
                    
            except Exception as e:
                logger.error(f"Error processing matchup row {idx}: {e}")
                continue
    
    return df
