import pandas as pd
import requests
import json
import os

CURRENT_YEAR = "2026"

def scrape_standings():
    print("Scraping Official F1 Standings...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/drivers.html"
    
    try:
        # Pandas magically grabs the HTML table from F1.com
        tables = pd.read_html(url)
        df = tables[0]
        
        standings_list = []
        
        for index, row in df.iterrows():
            # F1 formats names like "Max Verstappen VER". We need to split it for the UI.
            name_parts = str(row['Driver']).split(' ')
            code = name_parts[-1] # The 3-letter code is always last
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

        # We wrap it in the exact Ergast/Jolpica structure so your app.js doesn't break!
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
        print("✅ Standings updated instantly from Official F1 Site!")

    except Exception as e:
        print(f"❌ Failed to scrape standings: {e}")

def scrape_race_results():
    print("Scraping Official F1 Race Winners...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/races.html"
    
    try:
        tables = pd.read_html(url)
        df = tables[0]
        
        races_list = []
        
        for index, row in df.iterrows():
            name_parts = str(row['Winner']).split(' ')
            code = name_parts[-1]
            given_name = name_parts[0]
            family_name = " ".join(name_parts[1:-1])

            # For the results tab, we just need the Grand Prix name and the winner
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

        with open("api/results.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Race Results updated instantly from Official F1 Site!")

    except Exception as e:
        print(f"❌ Failed to scrape results: {e}")

if __name__ == "__main__":
    scrape_standings()
    scrape_race_results()
    
    # You can still fetch the 'current.json' calendar from Jolpica since schedules don't change!
    try:
        cal = requests.get("https://api.jolpi.ca/ergast/f1/current.json").json()
        with open("api/current.json", "w") as f:
            json.dump(cal, f, indent=2)
        print("✅ Calendar synced from Jolpica!")
    except:
        pass
