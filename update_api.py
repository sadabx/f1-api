import pandas as pd
import requests
import json
import os
import sys

# Get current year dynamically so it never breaks on season transitions
CURRENT_YEAR = "2026"

def scrape_standings():
    print("Scraping Official F1 Standings...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/drivers.html"
    
    try:
        tables = pd.read_html(url)
        if not tables:
            raise ValueError("No tables found on the F1 standings page.")
        df = tables[0]
        
        standings_list = []
        for index, row in df.iterrows():
            name_parts = str(row['Driver']).split(' ')
            code = name_parts[-1]
            given_name = name_parts[0]
            family_name = " ".join(name_parts[1:-1])
            
            standings_list.append({
                "position": str(row['Pos']),
                "points": str(row['PTS']),
                "Driver": {
                    "givenName": given_name,
                    "familyName": family_name,
                    "code": code
                },
                "Constructors": [{"name": str(row['Car'])}]
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
        raise e # Force the script to fail so GitHub workflow stops here

def scrape_race_results():
    print("Scraping Official F1 Race Winners...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/races.html"
    
    try:
        tables = pd.read_html(url)
        if not tables:
            raise ValueError("No tables found on the F1 race results page.")
        df = tables[0]
        
        races_list = []
        for index, row in df.iterrows():
            name_parts = str(row['Winner']).split(' ')
            code = name_parts[-1]
            given_name = name_parts[0]
            family_name = " ".join(name_parts[1:-1])

            races_list.append({
                "raceName": str(row['Grand Prix']) + " Grand Prix",
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
        
        # Sync calendar safely
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
        sys.exit(1) # Tell GitHub Actions that the compilation failed
