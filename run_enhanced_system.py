#!/usr/bin/env python3
"""
MLB Home Run Prediction System - Enhanced Version
Integrates all enhanced components into a complete prediction workflow
"""

import os
import sys
import argparse
import pandas as pd
import subprocess
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/enhanced_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("enhanced_system")

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Enhanced MLB HR Prediction System")
    
    # Mode options
    mode_group = parser.add_argument_group("Mode Options")
    mode_group.add_argument("--collect-data", action="store_true", help="Collect detailed pitch data")
    mode_group.add_argument("--train-model", action="store_true", help="Train enhanced prediction model")
    mode_group.add_argument("--predict", action="store_true", help="Generate predictions")
    mode_group.add_argument("--in-game", action="store_true", help="Apply in-game adjustments")
    mode_group.add_argument("--all", action="store_true", help="Run complete workflow")
    
    # Data collection options
    data_group = parser.add_argument_group("Data Collection Options")
    data_group.add_argument("--start-date", type=str, help="Start date for data collection (YYYY-MM-DD)")
    data_group.add_argument("--end-date", type=str, help="End date for data collection (YYYY-MM-DD)")
    data_group.add_argument("--days", type=int, default=7, help="Number of days to collect (default: 7)")
    
    # Prediction options
    pred_group = parser.add_argument_group("Prediction Options")
    pred_group.add_argument("--use-model", action="store_true", help="Use trained ML model (vs rule-based)")
    pred_group.add_argument("--real-time", action="store_true", help="Enable real-time updates")
    pred_group.add_argument("--update-interval", type=int, default=15, help="Minutes between updates")
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--output", type=str, help="Output directory")
    output_group.add_argument("--telegram", action="store_true", help="Send Telegram alerts")
    output_group.add_argument("--test", action="store_true", help="Run in test mode")
    
    return parser.parse_args()

def print_banner(text):
    """Print a visually distinct banner"""
    width = 60
    padding = (width - len(text)) // 2
    
    print("\n" + "=" * width)
    print(" " * padding + text)
    print("=" * width + "\n")

def run_data_collection(args):
    """Run the pitch data collection process"""
    print_banner("DATA COLLECTION")
    
    # Determine date range
    today = datetime.now().strftime("%Y-%m-%d")
    
    if args.start_date:
        start_date = args.start_date
        end_date = args.end_date or today
    else:
        # Use last 7 days by default
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        end_date = today
    
    print(f"Collecting pitch data from {start_date} to {end_date}")
    
    # Build command
    cmd = [
        "python3", "pitch_data_collector.py",
        "--start_date", start_date
    ]
    
    if args.end_date or start_date != end_date:
        cmd.extend(["--end_date", end_date])
    
    cmd.append("--analyze")  # Generate plate discipline metrics
    
    # Run data collection
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            logger.info("✅ Pitch data collection completed successfully")
            return True
        else:
            logger.error(f"❌ Pitch data collection failed with code {result.returncode}")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Error running pitch data collection: {e}")
        return False

def run_model_training(args):
    """Run the enhanced model training process"""
    print_banner("MODEL TRAINING")
    
    # Build command
    cmd = ["python3", "enhanced_train_model.py"]
    
    if args.output:
        cmd.extend(["--output", args.output])
    
    # Run training
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            logger.info("✅ Model training completed successfully")
            return True
        else:
            logger.error(f"❌ Model training failed with code {result.returncode}")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Error running model training: {e}")
        return False

def run_prediction(args):
    """Run the prediction process"""
    print_banner("HR PREDICTION")
    
    # Build command
    cmd = ["python3", "main.py"]
    
    if args.test:
        cmd.append("--test")
    
    if args.real_time:
        cmd.append("--realtime")
        cmd.extend(["--update-interval", str(args.update_interval)])
    
    # Run prediction
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            logger.info("✅ Prediction completed successfully")
            
            # Find latest prediction file
            results_dir = "results"
            prediction_files = [f for f in os.listdir(results_dir) if f.startswith("hr_predictions_") and f.endswith(".csv")]
            
            if prediction_files:
                # Sort by modification time, newest first
                prediction_files.sort(key=lambda x: os.path.getmtime(os.path.join(results_dir, x)), reverse=True)
                prediction_file = os.path.join(results_dir, prediction_files[0])
                return prediction_file
            else:
                logger.warning("⚠️ No prediction file found")
                return None
        else:
            logger.error(f"❌ Prediction failed with code {result.returncode}")
            return None
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Error running prediction: {e}")
        return None

def run_in_game_adjustments(args, prediction_file):
    """Run in-game adjustments"""
    print_banner("IN-GAME ADJUSTMENTS")
    
    if not prediction_file or not os.path.exists(prediction_file):
        logger.error("❌ No prediction file to adjust")
        return None
    
    # Build command
    cmd = [
        "python3", "in_game_adjustments.py",
        "--input", prediction_file
    ]
    
    # Generate output path
    base_name = os.path.splitext(os.path.basename(prediction_file))[0]
    output_path = f"results/adjusted_{base_name}.csv"
    cmd.extend(["--output", output_path])
    
    # Run adjustments
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            logger.info(f"✅ In-game adjustments completed successfully: {output_path}")
            return output_path
        else:
            logger.error(f"❌ In-game adjustments failed with code {result.returncode}")
            return None
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Error running in-game adjustments: {e}")
        return None

def run_real_time_updates(args, initial_file):
    """Run real-time updates in a loop"""
    if not args.real_time or not initial_file:
        return
        
    print_banner("REAL-TIME UPDATES")
    print(f"Starting real-time updates every {args.update_interval} minutes")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            # Wait for next update interval
            next_update = datetime.now() + timedelta(minutes=args.update_interval)
            print(f"Next update at {next_update.strftime('%H:%M:%S')}")
            
            time.sleep(args.update_interval * 60)
            
            # Run in-game adjustments
            print("\nRunning in-game updates...")
            adjusted_file = run_in_game_adjustments(args, initial_file)
            
            if adjusted_file:
                # Send updated Telegram alerts if enabled
                if args.telegram:
                    send_telegram_updates(adjusted_file)
    except KeyboardInterrupt:
        print("\nReal-time updates stopped by user")
    except Exception as e:
        logger.error(f"Error in real-time updates: {e}")

def send_telegram_updates(prediction_file):
    """Send Telegram alerts with updated predictions"""
    if not os.path.exists(prediction_file):
        logger.error(f"❌ Prediction file not found: {prediction_file}")
        return False
        
    # Build command
    cmd = ["python3", "telegram_alerts.py", "--input", prediction_file, "--update"]
    
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            logger.info("✅ Telegram alerts sent successfully")
            return True
        else:
            logger.error(f"❌ Telegram alerts failed with code {result.returncode}")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Error sending Telegram alerts: {e}")
        return False

def main():
    """Main function to run the enhanced system"""
    # Parse arguments
    args = parse_args()
    
    # Check if any mode was selected
    if not (args.collect_data or args.train_model or args.predict or args.in_game or args.all):
        print("No mode selected. Use --all for complete workflow or select specific modes.")
        parser.print_help()
        return 1
    
    # Create required directories
    for directory in ["logs", "data", "results", "models", "cache"]:
        os.makedirs(directory, exist_ok=True)
    
    # Print system banner
    print("\n" + "=" * 60)
    print("  ENHANCED MLB HOME RUN PREDICTION SYSTEM")
    print("  Running with the following components:")
    print(f"  - Data Collection: {'✅' if args.collect_data or args.all else '❌'}")
    print(f"  - Model Training: {'✅' if args.train_model or args.all else '❌'}")
    print(f"  - HR Prediction: {'✅' if args.predict or args.all else '❌'}")
    print(f"  - In-Game Adjustments: {'✅' if args.in_game or args.all else '❌'}")
    print(f"  - Real-Time Updates: {'✅' if args.real_time else '❌'}")
    print(f"  - Test Mode: {'✅' if args.test else '❌'}")
    print("=" * 60 + "\n")
    
    # Run components based on selected modes
    if args.collect_data or args.all:
        success = run_data_collection(args)
        if not success and args.all:
            logger.warning("⚠️ Data collection failed, but continuing with workflow")
    
    if args.train_model or args.all:
        success = run_model_training(args)
        if not success and args.all:
            logger.warning("⚠️ Model training failed, but continuing with workflow")
    
    if args.predict or args.all:
        prediction_file = run_prediction(args)
        
        if prediction_file:
            # Run in-game adjustments if requested
            if args.in_game or args.all:
                adjusted_file = run_in_game_adjustments(args, prediction_file)
                
                # Use adjusted file for real-time updates if available
                if adjusted_file:
                    prediction_file = adjusted_file
            
            # Start real-time updates if requested
            if args.real_time:
                run_real_time_updates(args, prediction_file)
        else:
            logger.error("❌ Prediction failed, cannot continue with in-game adjustments")
            if args.all:
                return 1
    
    print("\n" + "=" * 60)
    print("  ENHANCED MLB HR PREDICTION COMPLETED")
    print("=" * 60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
