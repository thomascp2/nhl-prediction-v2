"""
Data Fetchers Test Script
=========================
Tests NFL and MLB data fetchers to ensure they work properly
"""

import sys
from pathlib import Path

print("\n" + "="*70)
print("🏈⚾ NFL & MLB DATA FETCHERS - COMPREHENSIVE TEST")
print("="*70)

def test_nfl_fetchers():
    """Test NFL data fetchers"""
    print("\n" + "="*70)
    print("🏈 TESTING NFL DATA FETCHERS")
    print("="*70)

    nfl_path = Path(r"C:\Users\thoma\NFL-Model-v1")
    if not nfl_path.exists():
        print(f"❌ NFL directory not found: {nfl_path}")
        return False

    sys.path.insert(0, str(nfl_path))

    try:
        # Test 1: Game Schedule Fetcher
        print("\n📅 TEST 1: NFL Game Schedule Fetcher")
        print("-" * 70)
        from fetchers.fetch_nfl_game_schedule import fetch_games_for_week, save_games_to_db

        # Fetch Week 1 of 2024 season
        games = fetch_games_for_week(2024, 1)

        if games:
            print(f"✅ Successfully fetched {len(games)} games")
            print(f"   Sample: {games[0]['home_team']} vs {games[0]['away_team']}")

            # Save to database
            saved = save_games_to_db(games)
            print(f"✅ Saved {saved} games to database")
        else:
            print("⚠️  No games found (check API connection)")

        # Test 2: Player Stats Fetcher
        print("\n👤 TEST 2: NFL Player Stats Fetcher")
        print("-" * 70)
        from fetchers.fetch_nfl_player_stats import fetch_team_roster

        # Fetch Kansas City Chiefs roster
        players = fetch_team_roster('KC', 2024)

        if players:
            print(f"✅ Successfully fetched roster: {len(players)} players")
            qbs = [p for p in players if p['position'] == 'QB']
            if qbs:
                print(f"   Sample QB: {qbs[0]['player_name']}")
        else:
            print("⚠️  No players found (check API connection)")

        print("\n" + "="*70)
        print("✅ NFL FETCHERS TEST COMPLETE")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n❌ NFL FETCHERS TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mlb_fetchers():
    """Test MLB data fetchers"""
    print("\n" + "="*70)
    print("⚾ TESTING MLB DATA FETCHERS")
    print("="*70)

    mlb_path = Path(r"C:\Users\thoma\MLB-Model-v1")
    if not mlb_path.exists():
        print(f"❌ MLB directory not found: {mlb_path}")
        return False

    sys.path.insert(0, str(mlb_path))

    try:
        # Test 1: Game Schedule Fetcher
        print("\n📅 TEST 1: MLB Game Schedule Fetcher")
        print("-" * 70)
        from fetchers.fetch_mlb_game_schedule import fetch_games_for_date, save_games_to_db

        # Fetch Opening Day 2025 (or try a date that has games)
        test_date = "2025-04-01"  # Try early April
        games = fetch_games_for_date(test_date)

        if games:
            print(f"✅ Successfully fetched {len(games)} games")
            print(f"   Sample: {games[0]['home_team']} vs {games[0]['away_team']}")
            if games[0]['home_pitcher']:
                print(f"   Starting Pitchers: {games[0]['home_pitcher']} ({games[0]['home_pitcher_hand']}) vs {games[0]['away_pitcher']} ({games[0]['away_pitcher_hand']})")

            # Save to database
            saved = save_games_to_db(games)
            print(f"✅ Saved {saved} games to database")
        else:
            print(f"⚠️  No games found for {test_date} (may not be scheduled yet)")

        # Test 2: Player Stats Fetcher
        print("\n👤 TEST 2: MLB Player Stats Fetcher")
        print("-" * 70)
        from fetchers.fetch_mlb_player_stats import fetch_team_roster

        # Fetch Los Angeles Dodgers roster
        players = fetch_team_roster('LAD', 2025)

        if players:
            print(f"✅ Successfully fetched roster: {len(players)} players")
            pitchers = [p for p in players if p['player_type'] == 'pitcher']
            batters = [p for p in players if p['player_type'] == 'batter']
            print(f"   Pitchers: {len(pitchers)}, Batters: {len(batters)}")
            if pitchers:
                print(f"   Sample Pitcher: {pitchers[0]['player_name']}")
        else:
            print("⚠️  No players found (check API connection)")

        print("\n" + "="*70)
        print("✅ MLB FETCHERS TEST COMPLETE")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n❌ MLB FETCHERS TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\nThis script will test that the data fetchers work properly.")
    print("It will fetch a small amount of data to verify API connections.\n")

    # Test NFL
    nfl_ok = test_nfl_fetchers()

    # Test MLB
    mlb_ok = test_mlb_fetchers()

    # Final summary
    print("\n" + "="*70)
    print("📊 FINAL SUMMARY")
    print("="*70)

    if nfl_ok and mlb_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ NFL Fetchers: Working")
        print("✅ MLB Fetchers: Working")
        print("\n🚀 NEXT STEPS:")
        print("   1. Run full backtest on 2024-2025 NFL season")
        print("   2. Run full backtest on 2025 MLB season")
        print("   3. Validate accuracy (NFL: 55-65%, MLB: 58-62%)")
        print("   4. Deploy live if backtest passes!")
    else:
        print("\n⚠️  SOME TESTS FAILED:")
        if not nfl_ok:
            print("   ❌ NFL fetchers need attention")
        if not mlb_ok:
            print("   ❌ MLB fetchers need attention")
        print("\n   Review errors above and check:")
        print("   - Internet connection")
        print("   - API availability")
        print("   - File paths are correct")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
