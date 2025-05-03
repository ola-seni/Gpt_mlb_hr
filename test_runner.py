# test_runner.py - For local testing before pushing to GitHub
import os
import sys
import dotenv
from datetime import datetime

def setup_test_environment():
    """Setup test environment for local runs"""
    # Load environment variables from .env file if available
    dotenv.load_dotenv()
    
    # Check for required environment variables
    required_vars = ["OPENWEATHER_API", "BOT_TOKEN", "CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file or set them in your environment")
        return False
    
    # Force test mode
    os.environ["TEST_MODE"] = "1"
    
    return True

def run_test():
    """Run the application in test mode"""
    print(f"🧪 Running in TEST MODE at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Import main and run with test flag
        sys.argv.append("--test")
        import main
        main.main()
        print("✅ Test completed successfully")
        return True
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    if setup_test_environment():
        success = run_test()
        sys.exit(0 if success else 1)
    else:
        sys.exit(1)
