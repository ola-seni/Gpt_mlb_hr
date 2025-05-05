# ⚾ GPT-Driven MLB Home Run Predictor

This project predicts which MLB players are most likely to hit home runs on any given game day using a combination of Statcast data, advanced metrics (e.g., ISO, barrel %, EV), matchup analysis, and weather/park conditions. Fully automated and enhanced with optional Telegram alerts.

---

## 🔧 Features

- ✅ Pulls daily matchups and confirmed lineups from MLB Stats API
- 📊 Analyzes advanced batter/pitcher metrics from `pybaseball`
- 🌬️ Incorporates park factors and weather data (OpenWeather API)
- 🧠 Predicts HR likelihood using machine learning or rule-based scoring
- 🧵 Categorizes hitters as `Lock 🔒`, `Sleeper 🌙`, or `Risky ⚠️`
- 📬 Sends alerts via Telegram (optional)
- 📈 Logs predictions and accuracy over time (for future model retraining)
- 🖥️ Streamlit dashboard for visual analysis (optional)

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/ola-seni/Gpt_mlb_hr.git
cd Gpt_mlb_hr

pip install -r requirements.txt

OPENWEATHER_API=your_api_key_here
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id

python3 main.py

Gpt_mlb_hr/
├── main.py                  # Entry point — orchestrates the entire prediction
├── fetch_statcast_data.py  # Gathers Statcast metrics
├── predictor.py            # Calculates HR score and probability
├── telegram_alerts.py      # Sends categorized HR alerts
├── lineup_parser.py        # Pulls confirmed/projected lineups
├── train_model.py          # ML training and joblib export
├── utils.py                # Helper functions
├── dashboard.py            # (Optional) Streamlit dashboard
├── requirements.txt
└── .env                    # Your secrets (ignored)



