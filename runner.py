# runner.py - Improved error handling wrapper for GitHub Actions
import sys
import os
import traceback
import requests
from datetime import datetime

def send_error_notification(error_message):
    """Send error notification via Telegram if credentials exist"""
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    if bot_token and chat_id:
        try:
            message = f"⚠️ GitHub Actions Workflow Error:\n\n{error_message}"
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload)
            print(f"Error notification sent to Telegram")
        except Exception as e:
            print(f"Failed to send error notification: {e}")

def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = ["OPENWEATHER_API", "BOT_TOKEN", "CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def run_main():
    """Run the main.py script with proper error handling"""
    try:
        print(f"🚀 Starting MLB HR prediction workflow at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 Python version: {sys.version}")
        print(f"📂 Working directory: {os.getcwd()}")
        print(f"📁 Directory contents: {os.listdir('.')}")
        
        # Check environment variables
        check_environment_variables()
        
        # Import main module
        print("📦 Importing main module...")
        import main
        
        # Run main function
        print("▶️ Running main function...")
        main.main()
        
        print("✅ Workflow completed successfully")
        return 0
    except EnvironmentError as e:
        error_message = f"Environment Error: {str(e)}"
        print(f"❌ {error_message}")
        send_error_notification(error_message)
        return 1
    except ImportError as e:
        error_message = f"Import Error: {str(e)}\nCheck if all dependencies are installed correctly."
        print(f"❌ {error_message}")
        send_error_notification(error_message)
        return 1
    except Exception as e:
        error_message = f"Unhandled Exception: {str(e)}\n\n{traceback.format_exc()}"
        print(f"❌ {error_message}")
        send_error_notification(error_message)
        return 1

if __name__ == "__main__":
    sys.exit(run_main())
