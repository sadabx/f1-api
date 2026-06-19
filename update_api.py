import pandas as pd
import requests
import json
import os
import sys
import re

CURRENT_YEAR = "2026"

def get_column_by_substring(df, substrings):
    for sub in substrings:
        for i, col in enumerate(df.columns):
            if sub.lower() in str(col).lower():
                return i
    return None

def parse_driver_name(raw_name):
    name_parts = str(raw_name).strip().split(' ')
    # Filter out empty strings if any weird spacing occurs
    name_parts = [p for p in name_parts if p]
    
    code = name_parts[-1] if len(name_parts) > 1 else "UNK"
    given_name = name_parts[0] if len(name_parts) > 0 else ""
    family_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else (name_parts[1] if len(name_parts) == 2 else "")
    return given_name, family_name, code

def scrape_standings():
    print("Scraping Official F1 Standings...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/drivers.html"
    
    try:
        tables = pd.read_html(url)
        if not tables:
            raise ValueError("No tables found on the F1 standings page.")
        df = tables[0]
        
        pos_idx = get_column_by_substring(df, ['pos', 'position']) or 1
        driver_idx = get_column_by_substring(df, ['driver', 'name']) or 2
        car_idx = get_column_by_substring(df, ['car', 'team', 'constructor']) or 4
        pts_idx = get_column_by_substring(df, ['pts', 'points']) or 5
        
        standings_list = []
        for index, row in df.iterrows():
            given_name, family_name, code = parse_driver_name(row.iloc[driver_idx])
            
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
    print("Scraping Official F1 Race Winners and Podiums...")
    master_url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/races.html"
    
    try:
        # 1. Grab the HTML directly to find the specific race links and internal IDs
        html_content = requests.get(master_url, timeout=15).text
        
        # F1 URLs look like: /en/results.html/2026/races/1234/australia/race-result.html
        race_paths = re.findall(r'href="(/en/results\.html/\d{4}/races/\d+/[^/]+/race-result\.html)"', html_content)
        # Drop duplicates while maintaining calendar order
        race_paths = list(dict.fromkeys(race_paths))
        
        races_list = []
        
        for path in race_paths:
            detail_url = f"https://www.formula1.com{path}"
            print(f"-> Scraping podium details from: {detail_url}")
            
            detail_tables = pd.read_html(detail_url)
            if not detail_tables:
                continue
            race_df = detail_tables[0]
            
            # Find relevant column placements
            pos_idx = get_column_by_substring(race_df, ['pos', 'position']) or 1
            driver_idx = get_column_by_substring(race_df, ['driver', 'name']) or 2
            
            # Dynamically determine the Grand Prix Name from the URL path
            gp_slug = path.split('/')[-2].replace('-', ' ').title()
            gp_name = gp_slug if "grand prix" in gp_slug.lower() else f"{gp_slug} Grand Prix"
            # Clean up known casing anomalies (like Usa -> United States)
            if "Usa" in gp_name: gp_name = gp_name.replace("Usa", "United States")
            
            podium_results = []
            
            # 2. Extract exactly the top 3 rows (P1, P2, P3)
            for i in range(min(3, len(race_df))):
                row = race_df.iloc[i]
                given_name, family_name, code = parse_driver_name(row.iloc[driver_idx])
                
                podium_results.append({
                    "position": str(row.iloc[pos_idx]),
                    "Driver": {
                        "givenName": given_name,
                        "familyName": family_name,
                        "code": code
                    }
                })
                
            races_list.append({
                "raceName": gp_name,
                "Results": podium_results
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
        print("✅ Full Race Results (Podiums) updated successfully.")

    except Exception as e:
        print(f"❌ Failed to scrape race details: {e}")
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
