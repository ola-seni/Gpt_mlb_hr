# cache_utils.py

import json
import os
from datetime import datetime, timezone, timedelta

def load_json_cache(filepath, max_age_days=30):
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r") as f:
            raw_cache = json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ Corrupted cache file: {filepath}. Starting fresh.")
        return {}

    # Filter out stale entries
    valid_cache = {}
    now = datetime.now(timezone.utc)
    for key, entry in raw_cache.items():
        timestamp_str = entry.get("timestamp")
        if not timestamp_str:
            continue
        try:
            ts = datetime.fromisoformat(timestamp_str)
            # Make ts timezone aware if it isn't already
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if now - ts <= timedelta(days=max_age_days):
                valid_cache[key] = entry
        except Exception:
            continue

    return valid_cache

def save_json_cache(cache, filepath):
    try:
        # Attach updated timestamps before saving
        # Use datetime.now(UTC) instead of utcnow()
        now = datetime.now(timezone.utc).isoformat()
        timed_cache = {
            key: {
                "data": val["data"] if isinstance(val, dict) and "data" in val else val,
                "timestamp": val.get("timestamp", now)
            } for key, val in cache.items()
        }

        with open(filepath, "w") as f:
            json.dump(timed_cache, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving cache to {filepath}: {e}")
