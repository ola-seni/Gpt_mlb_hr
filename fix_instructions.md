# MLB HR Predictor Troubleshooting Guide

This guide will help you fix the issues with unknown pitchers and incorrect stadium data in your MLB Home Run Prediction system.

## Quick Fix Steps

1. **Replace the files with updated versions:**
   - Replace `lineup_parser.py` with the updated version
   - Replace `projected_lineups.py` with the updated version
   - Replace `weather.py` with the updated version
   - Replace `main.py` with the updated version (or keep your existing one if you've made custom changes)

2. **Run the diagnostic test script:**
   ```bash
   python test_mlb_api.py
   ```
   This will test your connections to the MLB Stats API and OpenWeather API and help identify any issues.

3. **Run with debug mode enabled:**
   ```bash
   python main.py --debug
   ```
   This will show detailed logs about what's happening during the API calls.

## What's Been Fixed

The updated files include:

1. **Improved API Error Handling:**
   - Added retry logic with exponential backoff
   - Better error logging
   - Fallbacks when primary data sources fail

2. **Enhanced Ballpark Detection:**
   - More robust logic to identify team codes from ballpark names
   - Preservation of ballpark data during DataFrame merges
   - Multiple backup methods to determine the venue

3. **Better Data Caching:**
   - Smart caching of API responses
   - Age-based cache invalidation
   - Structured fallback data when APIs fail

4. **Diagnostic Logging:**
   - Detailed log messages to track execution flow
   - Specific messages when API calls fail
   - Column-level debugging to identify missing data

## Environment Setup

Make sure your `.env` file includes:

```
OPENWEATHER_API=your_api_key_here
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
```

The OPENWEATHER_API is particularly important for getting accurate weather data for each ballpark.

## Common Issues & Solutions

### Unknown Pitcher

This happens when:
- The MLB Stats API fails to return lineup data
- The data structure from the API has changed
- The pitcher's name isn't correctly extracted from the response

Solution: The updated code now tries multiple ways to get pitcher information and falls back to accurate test data when needed.

### Incorrect Stadium Data

This happens when:
- The ballpark data is lost during DataFrame merges
- The team code can't be mapped to a stadium
- The API returns unexpected stadium information

Solution: The updated code preserves ballpark data throughout processing and has multiple methods to determine the correct stadium.

### API Connection Failures

This happens when:
- MLB Stats API changes their endpoints
- Your internet connection has issues
- MLB's servers are experiencing problems

Solution: The updated code includes retry logic and better fallbacks to handle API issues gracefully.

## Advanced Debugging

If you're still having issues:

1. Check the log files:
   - `mlb_hr_predictions.log`
   - `mlb_api_test.log`

2. Look at the test results in the `test_results` directory:
   - API test results
   - Lineup structure analysis

3. Try running in test mode to see if the core logic works:
   ```bash
   python main.py --test
   ```

4. Try manually accessing the MLB Stats API to see if it's available:
   ```bash
   curl "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=$(date +%Y-%m-%d)&hydrate=lineups"
   ```

## Contact for Support

If you continue to experience issues, please provide:
1. The contents of your log files
2. The test results from `test_mlb_api.py`
3. A description of the specific errors you're seeing
