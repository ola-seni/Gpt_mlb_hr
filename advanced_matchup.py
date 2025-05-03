# advanced_matchup.py
import pandas as pd
import numpy as np
from pybaseball import statcast_batter, statcast_pitcher
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("advanced_matchup")

class PitchMatchupAnalyzer:
    """Analyze batter vs pitcher matchups at the pitch level"""
    
    def __init__(self, batter_id, pitcher_id, lookback_days=120):
        """
        Initialize the analyzer with player IDs.
        
        Args:
            batter_id (int): MLB batter ID
            pitcher_id (int): MLB pitcher ID
            lookback_days (int): How many days to look back
        """
        self.batter_id = batter_id
        self.pitcher_id = pitcher_id
        self.lookback_days = lookback_days
        self.batter_data = None
        self.pitcher_data = None
        self.direct_matchup_data = None
        
    def fetch_data(self):
        """Fetch required data for analysis"""
        logger.info(f"Fetching data for batter {self.batter_id} vs pitcher {self.pitcher_id}")
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
        
        try:
            # Get batter data
            self.batter_data = statcast_batter(start_date, end_date, self.batter_id)
            logger.info(f"✅ Got {len(self.batter_data)} batter records")
            
            # Get pitcher data
            self.pitcher_data = statcast_pitcher(start_date, end_date, self.pitcher_id)
            logger.info(f"✅ Got {len(self.pitcher_data)} pitcher records")
            
            # Get direct matchup data if available
            # This requires a custom query that's not directly supported by pybaseball
            # In a real implementation, we would fetch this data from a StatCast API query
            # For now, we'll create a placeholder
            self.direct_matchup_data = pd.DataFrame()
            
            return True
        
        except Exception as e:
            logger.error(f"Error fetching matchup data: {e}")
            return False
    
    def analyze_pitch_types(self):
        """Analyze performance against specific pitch types"""
        if self.batter_data is None or self.pitcher_data is None:
            if not self.fetch_data():
                return {}
        
        results = {}
        
        try:
            # Get batter performance by pitch type
            batter_vs_pitch = {}
            if not self.batter_data.empty and 'pitch_type' in self.batter_data.columns:
                for pitch_type, group in self.batter_data.groupby('pitch_type'):
                    if pitch_type and not pd.isna(pitch_type) and len(group) >= 5:
                        # Calculate slug, whiff rate, etc.
                        hits = group['events'].isin(['single', 'double', 'triple', 'home_run']).sum()
                        at_bats = len(group[group['events'].notna()])
                        bases = (
                            group['events'].eq('single').sum() * 1 +
                            group['events'].eq('double').sum() * 2 +
                            group['events'].eq('triple').sum() * 3 +
                            group['events'].eq('home_run').sum() * 4
                        )
                        
                        batter_vs_pitch[pitch_type] = {
                            'count': len(group),
                            'avg': hits / max(1, at_bats) if at_bats > 0 else 0,
                            'slg': bases / max(1, at_bats) if at_bats > 0 else 0,
                            'whiff_rate': group['description'].eq('swinging_strike').sum() / 
                                         max(1, group['description'].isin(['swinging_strike', 'hit_into_play']).sum()),
                            'hr_rate': group['events'].eq('home_run').sum() / max(1, at_bats) if at_bats > 0 else 0
                        }
            
            # Get pitcher tendencies by pitch type
            pitcher_pitch_mix = {}
            if not self.pitcher_data.empty and 'pitch_type' in self.pitcher_data.columns:
                pitch_counts = self.pitcher_data['pitch_type'].value_counts(normalize=True)
                total_pitches = len(self.pitcher_data)
                
                for pitch_type, pct in pitch_counts.items():
                    if pitch_type and not pd.isna(pitch_type):
                        pitch_group = self.pitcher_data[self.pitcher_data['pitch_type'] == pitch_type]
                        
                        pitcher_pitch_mix[pitch_type] = {
                            'usage': pct,
                            'count': len(pitch_group),
                            'avg_speed': pitch_group['release_speed'].mean() if 'release_speed' in pitch_group.columns else None,
                            'avg_spin': pitch_group['release_spin_rate'].mean() if 'release_spin_rate' in pitch_group.columns else None,
                            'whiff_rate': pitch_group['description'].eq('swinging_strike').sum() / 
                                         max(1, pitch_group['description'].isin(['swinging_strike', 'hit_into_play']).sum()),
                            'hr_allowed': pitch_group['events'].eq('home_run').sum() / 
                                        max(1, len(pitch_group[pitch_group['events'].notna()]))
                        }
            
            # Combine batter and pitcher data for each pitch type
            combined_analysis = {}
            all_pitch_types = set(list(batter_vs_pitch.keys()) + list(pitcher_pitch_mix.keys()))
            
            for pitch_type in all_pitch_types:
                batter_data = batter_vs_pitch.get(pitch_type, {})
                pitcher_data = pitcher_pitch_mix.get(pitch_type, {})
                
                if batter_data or pitcher_data:
                    # Calculate matchup score for this pitch type
                    matchup_score = 0.0
                    factors = 0
                    
                    # Batter's success vs this pitch
                    if 'slg' in batter_data:
                        matchup_score += batter_data['slg'] * 0.3
                        factors += 0.3
                        
                    if 'hr_rate' in batter_data:
                        matchup_score += batter_data['hr_rate'] * 10 * 0.4  # Scale up HR rate
                        factors += 0.4
                    
                    # Pitcher's weakness with this pitch
                    if 'hr_allowed' in pitcher_data:
                        matchup_score += pitcher_data['hr_allowed'] * 10 * 0.3  # Scale up HR rate
                        factors += 0.3
                    
                    # Normalize score
                    if factors > 0:
                        matchup_score = matchup_score / factors
                    
                    combined_analysis[pitch_type] = {
                        'batter': batter_data,
                        'pitcher': pitcher_data,
                        'matchup_score': round(matchup_score, 3),
                        'usage_likelihood': pitcher_data.get('usage', 0)
                    }
            
            # Calculate overall matchup score
            overall_score = 0.0
            total_weight = 0.0
            
            for pitch_type, data in combined_analysis.items():
                weight = data['usage_likelihood']
                overall_score += data['matchup_score'] * weight
                total_weight += weight
                
            if total_weight > 0:
                overall_score = overall_score / total_weight
            
            results = {
                'pitch_analysis': combined_analysis,
                'overall_matchup_score': round(overall_score, 3)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing pitch types: {e}")
            return {}
    
    def analyze_pitcher_type_performance(self):
        """Analyze how the batter performs against this pitcher type"""
        if self.pitcher_data is None:
            if not self.fetch_data():
                return {}
        
        try:
            # Determine pitcher type
            pitcher_type = self._classify_pitcher()
            
            # Get batter performance vs this pitcher type
            # This would typically require historical data beyond what's easily accessible
            # For a real implementation, we would use a database of pitcher classifications
            
            return {
                'pitcher_type': pitcher_type,
                'batter_vs_type': {
                    'avg': 0.0,  # Placeholder
                    'slg': 0.0,  # Placeholder
                    'hr_rate': 0.0  # Placeholder
                }
            }
        
        except Exception as e:
            logger.error(f"Error analyzing pitcher type: {e}")
            return {}
    
    def _classify_pitcher(self):
        """Classify the pitcher type based on their pitch usage and velocities"""
        if self.pitcher_data is None or self.pitcher_data.empty:
            return "Unknown"
        
        try:
            # Get pitch mix
            if 'pitch_type' in self.pitcher_data.columns:
                pitch_mix = self.pitcher_data['pitch_type'].value_counts(normalize=True).to_dict()
                
                # Get average fastball velocity
                fastball_velo = 0
                if 'FF' in pitch_mix and 'release_speed' in self.pitcher_data.columns:
                    fastballs = self.pitcher_data[self.pitcher_data['pitch_type'] == 'FF']
                    if not fastballs.empty:
                        fastball_velo = fastballs['release_speed'].mean()
                
                # Determine type based on pitch mix and velo
                if 'FF' in pitch_mix and pitch_mix['FF'] >= 0.60:
                    return "Fastball Heavy"
                
                if 'SL' in pitch_mix and pitch_mix['SL'] >= 0.35:
                    return "Slider Dominant"
                
                if 'CH' in pitch_mix and pitch_mix['CH'] >= 0.25:
                    return "Changeup Mixer"
                
                if 'CU' in pitch_mix and pitch_mix['CU'] >= 0.20:
                    return "Breaking Ball Pitcher"
                
                if fastball_velo >= 95:
                    return "Power Pitcher"
                
                return "Command Pitcher"
            
            return "Unknown"
            
        except Exception as e:
            logger.error(f"Error classifying pitcher: {e}")
            return "Unknown"
    
    def get_complete_analysis(self):
        """Perform complete matchup analysis"""
        return {
            'pitch_analysis': self.analyze_pitch_types(),
            'pitcher_type_analysis': self.analyze_pitcher_type_performance(),
            'batter_id': self.batter_id,
            'pitcher_id': self.pitcher_id
        }

def analyze_matchup(batter_id, pitcher_id):
    """Convenience function to analyze a matchup"""
    analyzer = PitchMatchupAnalyzer(batter_id, pitcher_id)
    return analyzer.get_complete_analysis()
