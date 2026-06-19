import pandas as pd
import requests
import json
import os
import sys

CURRENT_YEAR = "2026"

def get_column_by_substring(df, substrings):
    """Finds a column index matching any of the given substrings (case-insensitive)."""
    for sub in substrings:
        for i, col in enumerate(df.columns):
            if sub.lower() in str(col).lower():
                return i
    return None

def scrape_standings():
    print("Scraping Official F1 Standings...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/drivers.html"
    
    try:
        tables = pd.read_html(url)
        if not tables:
            raise ValueError("No tables found on the F1 standings page.")
        df = tables[0]
        
        # Dynamically detect columns by keyword matching
        pos_idx = get_column_by_substring(df, ['pos', 'position']) or 1
        driver_idx = get_column_by_substring(df, ['driver', 'name']) or 2
        car_idx = get_column_by_substring(df, ['car', 'team', 'constructor']) or 4
        pts_idx = get_column_by_substring(df, ['pts', 'points']) or 5
        
        standings_list = []
        for index, row in df.iterrows():
            raw_driver = str(row.iloc[driver_idx])
            name_parts = raw_driver.split(' ')
            
            # Extract 3-letter broadcast code (usually last word)
            code = name_parts[-1] if len(name_parts) > 1 else "UNK"
            given_name = name_parts[0] if len(name_parts) > 0 else ""
            family_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else (name_parts[1] if len(name_parts) == 2 else "")
            
            standings_list.append({
                "position": str(row.iloc[pos_idx]),
                "points": str(row.iloc[pts_idx]),
                "Driver": {
                    "givenName": given_name,
                    "familyName": family_name,
                    "code": code
                },
                "Constructors": [{"name": str(row.iloc[car_idx])}]
            })

        ergast_json = {
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": [{"DriverStandings": standings_list}]
                }
            }
        }

        os.makedirs("api", exist_ok=True)
        with open("api/standings.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Standings updated successfully.")

    except Exception as e:
        print(f"❌ Failed to scrape standings: {e}")
        raise e

def scrape_race_results():
    print("Scraping Official F1 Race Winners...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/races.html"
    
    try:
        tables = pd.read_html(url)
        if not tables:
            raise ValueError("No tables found on the F1 race results page.")
        df = tables[0]
        
        # Dynamically detect columns by keyword matching
        gp_idx = get_column_by_substring(df, ['grand prix', 'race', 'location']) or 1
        winner_idx = get_column_by_substring(df, ['winner', 'driver']) or 3
        
        races_list = []
        for index, row in df.iterrows():
            raw_winner = str(row.iloc[winner_idx])
            name_parts = raw_winner.split(' ')
            
            code = name_parts[-1] if len(name_parts) > 1 else "UNK"
            given_name = name_parts[0] if len(name_parts) > 0 else ""
            family_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else (name_parts[1] if len(name_parts) == 2 else "")

            gp_name = str(row.iloc[gp_idx])
            if not gp_name.lower().endswith("grand prix"):
                gp_name += " Grand Prix"

            races_list.append({
                "raceName": gp_name,
                "Results": [
                    {
                        "position": "1",
                        "Driver": {
                            "givenName": given_name,
                            "familyName": family_name,
                            "code": code
                        }
                    }
                ]
            })

        ergast_json = {
            "MRData": {
                "RaceTable": {
                    "Races": races_list
                }
            }
        }

        os.makedirs("api", exist_ok=True)
        with open("api/results.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Race Results updated successfully.")

    except Exception as e:
        print(f"❌ Failed to scrape results: {e}")
        raise e

if __name__ == "__main__":
    try:
        scrape_standings()
        scrape_race_results()
        
        print("Syncing Calendar from Jolpica...")
        os.makedirs("api", exist_ok=True)
        cal_res = requests.get("https://api.jolpi.ca/ergast/f1/current.json", timeout=15)
        if cal_res.status_code == 200:
            with open("api/current.json", "w", encoding="utf-8") as f:
                json.dump(cal_res.json(), f, indent=2)
            print("✅ Calendar synced.")
        else:
            print("⚠️ Jolpica calendar endpoint down, skipping calendar sync.")
            
    except Exception as main_error:
        print(f"💥 Critical API build failure: {main_error}")
        sys.exit(1)
