# run_enhanced_hr_predictor.py
import os
import sys
import argparse
from datetime import datetime, timedelta

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced MLB Home Run Prediction")
    
    parser.add_argument("--backtest", action="store_true", 
                        help="Run backtesting on historical data")
    parser.add_argument("--train", action="store_true", 
                        help="Train advanced models using historical data")
    parser.add_argument("--analyze", action="store_true", 
                        help="Analyze feature importance")
    parser.add_argument("--predict", action="store_true", 
                        help="Make predictions for today's games using enhanced model")
    parser.add_argument("--start_date", type=str, 
                        help="Start date for backtesting (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, 
                        help="End date for backtesting (YYYY-MM-DD)")
    parser.add_argument("--test", action="store_true", 
                        help="Run in test mode with sample data")
    
    return parser.parse_args()

def print_banner():
    """Print an ASCII art welcome banner."""
    banner = """
    ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 
      _________________  _____    _______    _     _______
     / ____/ ____/__  / / ___/   / ____/ |  / /__  / ____/___ ___  _____
    / /   / /_    /_ < / __ \   / __/  | | / / _ \/ /   / __ `/ / / / _ \\
   / /___/ __/  ___/ // /_/ /  / /_    | |/ /  __/ /___/ /_/ / /_/ /  __/
   \____/_/    /____/ \____/  /_/      |___/\___/\____/\__,_/\__, /\___/ 
                                                             /____/       
    ENHANCED MLB HOME RUN PREDICTOR
    ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 
    """
    print(banner)

def check_dependencies():
    """Verify all required modules are installed."""
    required_modules = [
        "pandas", "pybaseball", "joblib", "scikit-learn",
        "matplotlib", "seaborn", "tqdm", "xgboost", "lightgbm",
        "requests"
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("Please install them with: pip install " + " ".join(missing))
        return False
    
    return True

def prepare_directories():
    """Ensure all necessary directories exist."""
    dirs = ["models", "backtest_results", "feature_analysis", "results", "cache"]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
    return True

def run_backtest(start_date=None, end_date=None):
    """Run backtesting on historical data."""
    # Default dates if not provided
    if not start_date:
        # Use a 30-day period one year ago
        last_year = datetime.now() - timedelta(days=365)
        start_date = (last_year - timedelta(days=15)).strftime("%Y-%m-%d")
        end_date = (last_year + timedelta(days=15)).strftime("%Y-%m-%d")
    elif not end_date:
        # Use a 30-day period from the provided start date
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = (start_datetime + timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"📅 Running backtesting from {start_date} to {end_date}")
    
    # Import here to avoid circular imports
    from backtest import run_backtesting
    
    return run_backtesting(start_date, end_date)

def analyze_features(data_path=None):
    """Analyze feature importance."""
    print("🔍 Analyzing feature importance...")
    
    # Import feature importance analyzer
    from feature_importance import analyze_feature_importance
    
    return analyze_feature_importance(data_path)

def train_models(data_path=None):
    """Train advanced models on historical data."""
    print("🧠 Training advanced models...")
    
    # Import model trainer
    from advanced_models import train_advanced_models
    
    return train_advanced_models(data_path)

def make_predictions(test_mode=False):
    """Make predictions for today's games using the enhanced model."""
    print("🔮 Making predictions for today's games...")
    
    # Check if enhanced model exists
    if not os.path.exists("models/model_meta.json"):
        print("⚠️ Enhanced model not found. Running with default model.")
    
    # Add model path to system path
    sys.path.append(os.path.join(os.getcwd(), "models"))
    
    # Import the original main module
    import main as original_main
    
    # Run the original prediction pipeline with the --test flag if requested
    if test_mode:
        sys.argv.append("--test")
    
    # Run the original main function
    original_main.main()
    
    return True

def main():
    """Main orchestration function."""
    print_banner()
    
    # Parse arguments
    args = parse_args()
    
    # Check for dependencies
    if not check_dependencies():
        return False
    
    # Prepare directories
    prepare_directories()
    
    # Default behavior: if no flags are provided, show help
    if not (args.backtest or args.train or args.analyze or args.predict):
        print("⚠️ No action specified. Use --backtest, --train, --analyze, or --predict")
        print("\nExample usage:")
        print("  python run_enhanced_hr_predictor.py --backtest --start_date 2023-05-01 --end_date 2023-05-15")
        print("  python run_enhanced_hr_predictor.py --analyze")
        print("  python run_enhanced_hr_predictor.py --train")
        print("  python run_enhanced_hr_predictor.py --predict")
        print("  python run_enhanced_hr_predictor.py --predict --test")
        print("  python run_enhanced_hr_predictor.py --backtest --train --analyze")
        return False
    
    # Track processing steps
    results = {}
    
    # Step 1: Backtesting
    if args.backtest:
        backtest_results = run_backtest(args.start_date, args.end_date)
        results["backtest"] = backtest_results is not None
        
        # Get the latest backtest file for further processing
        backtest_files = [f for f in os.listdir("backtest_results") if f.startswith("backtest_") and f.endswith(".csv")]
        if backtest_files:
            # Sort by modification time, newest first
            backtest_files.sort(key=lambda x: os.path.getmtime(os.path.join("backtest_results", x)), reverse=True)
            latest_backtest = os.path.join("backtest_results", backtest_files[0])
            results["backtest_file"] = latest_backtest
    
    # Step 2: Feature Analysis
    if args.analyze:
        data_path = results.get("backtest_file", None)
        feature_analysis = analyze_features(data_path)
        results["feature_analysis"] = feature_analysis is not None
    
    # Step 3: Train Advanced Models
    if args.train:
        data_path = results.get("backtest_file", None)
        models = train_models(data_path)
        results["models"] = models is not None
    
    # Step 4: Make Predictions
    if args.predict:
        predictions = make_predictions(args.test)
        results["predictions"] = predictions
    
    # Print summary
    print("\n📋 Processing Summary:")
    for step, status in results.items():
        if step == "backtest_file":
            continue
        print(f"  {'✅' if status else '❌'} {step.capitalize()}")
    
    return True

if __name__ == "__main__":
    main()
