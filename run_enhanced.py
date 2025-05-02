#!/usr/bin/env python3
"""
Enhanced MLB Home Run Prediction Runner
This script executes the enhanced version of the MLB HR prediction system.
"""

import sys
import os
import subprocess

def print_banner():
    """Print an ASCII art welcome banner."""
    banner = """
    ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 
     _____   _       _                          _ 
    | ____|/ \\   | | |_ __ | | ___  _ __   ___ ___  __| |
    |  _| / _ \\  | | | '_ \\| |/ _ \\| '_ \\ / __/ _ \\/ _` |
    | |__/ ___ \\ | | | | | | | (_) | | | | (_|  __/ (_| |
    |_____/_/   \\_\\|_|_| |_|_|\\___/|_| |_|\\___\\___|\\__,_|
                                                        
     __  __ _    ____   _   _ ____  
    |  \\/  | |  | __ ) | | | |  _ \\ 
    | |\\/| | |  |  _ \\ | |_| | |_) |
    | |  | | |__| |_) ||  _  |  _ < 
    |_|  |_|____|____/ |_| |_|_| \\_\\
                                 
    ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 ⚾️ 🔮 🏟️ 🔥 
    """
    print(banner)

def main():
    """Main function to run the enhanced predictions."""
    print_banner()
    
    # Check for python command
    python_cmd = "python3"
    if not is_command_available(python_cmd):
        python_cmd = "python"
        if not is_command_available(python_cmd):
            print("❌ Error: Python not found. Please install Python 3.")
            return False
    
    # Check if enhanced script exists
    if not os.path.exists("main_enhanced.py"):
        print("❌ Error: main_enhanced.py not found.")
        return False
    
    # Pass along any command-line arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Add test mode if requested
    if "--test" in args:
        print("🧪 Running in test mode.")
    else:
        print("🔮 Running enhanced MLB HR predictions...")
    
    # Run the enhanced script
    cmd = [python_cmd, "main_enhanced.py"] + args
    process = subprocess.run(cmd)
    
    # Check result
    if process.returncode == 0:
        print("\n✅ Enhanced MLB HR prediction completed successfully!")
        return True
    else:
        print(f"\n❌ Enhanced prediction failed with code: {process.returncode}")
        return False

def is_command_available(cmd):
    """Check if a command is available on the system."""
    try:
        subprocess.run([cmd, "--version"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
