import unicodedata

def generate_game_id(batter_name, pitcher_name, game_date):
    """Create a normalized game ID for batter vs pitcher matchups."""
    def normalize(name):
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8")
        return name.strip().lower().replace(" jr.", "").replace(".", "").replace(" ", "_")

    return f"{normalize(batter_name)}__vs__{normalize(pitcher_name)}__{game_date}"
