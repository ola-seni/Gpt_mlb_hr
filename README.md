# ⚾ Gpt_mlb_hr – Daily MLB Home Run Prediction System

**Gpt_mlb_hr** is a fully automated Python project that predicts which MLB players are most likely to hit home runs on any given day. It pulls real-time data, processes advanced statcast metrics, adjusts for weather and ballpark effects, and sends predictions via Telegram — all before game time.

---

## 🚀 Features

- 📅 **Daily game schedule parsing** via MLB Stats API
- 🔍 **Advanced prediction model** using:
  - Statcast data (ISO, barrel %, xHR, launch angle)
  - Batter-vs-pitcher (BvP) matchups
  - Park factors and recent form
  - Pitcher HR vulnerability and pitch types
- 🌤️ **Weather boosts** (wind, temp, elevation) via OpenWeather API
- ✅ **Confirmed starters only** (lineup-aware filtering)
- 📤 **Telegram alerts** sent with top HR picks
- 📈 **Scheduled runs** before early, afternoon, and night games using GitHub Actions

---

## 🧰 Requirements

Install dependencies locally with:

```bash
pip install -r requirements.txt
```

---

## 📦 Project Structure

```
Gpt_mlb_hr/
├── main.py                  # Main execution script
├── fetch_statcast_data.py   # Retrieves MLB player statistics
├── predictor.py             # Core prediction algorithm
├── weather.py               # Weather and park factor adjustments
├── telegram_alerts.py       # Notification system
├── lineup_parser.py         # Gets confirmed starting lineups
├── bullpen_tracker.py       # Analyzes bullpen quality
├── cache_utils.py           # Handles data caching
├── config.py                # Central configuration settings
├── dashboard.py             # Streamlit prediction performance tracker
├── requirements.txt         # Project dependencies
└── .github/
    └── workflows/
        └── mlb_hr_predictor.yml  # CI/CD automation
```

---

## ⚙️ GitHub Actions Automation

This project automatically runs daily at:

- 🕚 11:00 AM ET (before early games)
- 🕑 2:00 PM ET (before afternoon games)
- 🕔 5:00 PM ET (before evening games)

Configure secrets in your GitHub repo:

| Secret Name       | Description                     |
|-------------------|---------------------------------|
| `OPENWEATHER_API` | Your OpenWeather API key        |
| `BOT_TOKEN`       | Telegram Bot token              |
| `CHAT_ID`         | Telegram Chat ID (numeric only) |

---

## 📲 Telegram Alerts

Get a clean summary of the top home run picks for the day, delivered directly to your phone:

```
🔥 Top HR Predictions Today:
• Aaron Judge vs Clarke Schmidt: 0.74 | Lock 🔒
• Juan Soto vs Max Scherzer: 0.65 | Sleeper 🌙
```

---

## 🛠️ Development and Contribution

### Setup Development Environment

1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/Gpt_mlb_hr.git
cd Gpt_mlb_hr
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys
```
OPENWEATHER_API=your_api_key_here
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
```

### Running Tests

Future test suite will be available with:
```bash
python -m unittest discover tests
```

### Project Workflow

1. **Data Collection**: The system first checks for confirmed lineups from the MLB API
2. **Feature Engineering**: Enriches the data with Statcast metrics and pitcher analysis
3. **Weather Integration**: Fetches real-time weather data and calculates impact
4. **Prediction**: Generates HR probabilities and classifies them into tiers
5. **Notification**: Sends formatted alerts via Telegram
6. **Tracking**: Logs results daily for ongoing performance analysis

### Performance Dashboard

After collecting prediction data for at least a week, launch the Streamlit dashboard:

```bash
streamlit run dashboard.py
```

This provides visual tracking of prediction accuracy over time.

---

## 👨‍💻 Manual Use

You can also run it manually with:

```bash
python main.py
```

For testing without making API calls:

```bash
python main.py --test
```

---

## 📬 Contact

Built by [@ollyray](https://github.com/Ola-seni) using `pybaseball`, MLB Stats API, and GitHub Actions.