# calculate_pitch_matchup_score.py

def calculate_pitch_matchup_score(pitch_mix, batter_iso_by_pitch):
    """
    Weighted ISO score based on pitch types the pitcher throws and 
    how well the batter hits each pitch type.
    """
    score = 0
    total_weight = 0

    for pitch_type, pct in pitch_mix.items():
        batter_iso = batter_iso_by_pitch.get(pitch_type, 0.150)  # Fallback ISO
        score += batter_iso * pct
        total_weight += pct

    if total_weight == 0:
        return 0.150  # Default fallback score

    return round(score / total_weight, 3)
