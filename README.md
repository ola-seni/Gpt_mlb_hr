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
├── main.py
├── fetch_statcast_data.py
├── predictor.py
├── weather.py
├── telegram_alerts.py
├── lineup_parser.py
├── requirements.txt
└── .github/
    └── workflows/
        └── mlb_hr_predictor.yml
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

Get a clean summary of the top 10 home run picks for the day, delivered directly to your phone:

```
🔥 Top HR Predictions Today:
• Aaron Judge vs Clarke Schmidt: 0.74 | Lock 🔒
• Juan Soto vs Max Scherzer: 0.65 | Sleeper 🌙
```

---

## 👨‍💻 Manual Use

You can also run it manually with:

```bash
python main.py
```

---

## 📬 Contact

Built by [@YOUR_USERNAME](https://github.com/YOUR_USERNAME) using `pybaseball`, MLB Stats API, and GitHub Actions.
