"""
NBA Prediction System Initialization
=====================================

One-time setup script to initialize the NBA prediction system.

Steps:
1. Create database and schema
2. Load historical data (2024-2025 season to date)
3. Run backtest validation
4. Verify system is ready for live predictions

Run this once to set up the system.
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from setup_database import setup_database
from load_historical_data import HistoricalDataLoader
from run_backtest import NBABacktest


def initialize_system():
    """Initialize NBA prediction system."""

    print("=" * 60)
    print("🏀 NBA PREDICTION SYSTEM INITIALIZATION")
    print("=" * 60)

    # Step 1: Setup database
    print("\n📊 STEP 1: Setting up database...")
    setup_database()

    # Step 2: Load historical data
    print("\n📈 STEP 2: Loading historical data...")
    loader = HistoricalDataLoader()

    # Load from season start to yesterday
    season_start = "2024-10-22"
    yesterday = (datetime.now()).strftime("%Y-%m-%d")

    print(f"Loading data from {season_start} to {yesterday}")
    print("⚠️  This may take 10-15 minutes due to API rate limiting...")

    result = loader.load_season_data(season_start, yesterday)

    print(f"\n✅ Loaded {result['games']} games, {result['logs']} player logs")

    # Step 3: Run backtest
    print("\n🧪 STEP 3: Running backtest validation...")

    # Backtest on last 14 days (or available data)
    backtest_start = "2024-10-22"
    backtest_end = yesterday

    backtest = NBABacktest()
    backtest_results = backtest.run_backtest(backtest_start, backtest_end)

    # Step 4: Final verification
    print("\n" + "=" * 60)
    print("🎉 INITIALIZATION COMPLETE")
    print("=" * 60)

    print(f"\n✅ Database: Created")
    print(f"✅ Historical data: {result['logs']} player logs")
    print(f"✅ Backtest: {backtest_results['total_predictions']} predictions")
    print(f"✅ Accuracy: {backtest_results['overall_accuracy']:.1f}%")

    if backtest_results['overall_accuracy'] >= 55:
        print(f"\n🚀 SYSTEM READY FOR LIVE PREDICTIONS!")
        print(f"\nNext steps:")
        print(f"1. Run daily at 8 AM: python auto_grade_yesterday.py")
        print(f"2. Run daily at 10 AM: python generate_predictions_daily.py")
    else:
        print(f"\n⚠️  BACKTEST ACCURACY BELOW 55% - System needs refinement")
        print(f"Review feature extraction and prediction logic")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    initialize_system()
