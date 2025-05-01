# pitcher_suppression.py

def calculate_pitcher_suppression_score(row):
    """
    Calculate HR suppression score for a pitcher.
    Higher score = better at suppressing HRs.
    """
    try:
        hr9 = float(row.get("HR/9", 1.0))
        barrel = float(row.get("barrel_pct_allowed", 7.5))  # % value
        hard_contact = float(row.get("hard_contact_pct", 35.0))  # optional
        xfip = float(row.get("xFIP", 4.0))  # optional

        score = (
            (1 / (hr9 + 0.01)) * 0.4 +
            (1 / (barrel + 0.01)) * 0.3 +
            (1 / (hard_contact + 0.01)) * 0.2 +
            (1 / (xfip + 0.01)) * 0.1
        )
        return round(score, 3)
    except Exception as e:
        print(f"❌ Suppression score error: {e}")
        return 0.0
