import pandas as pd
import requests
import json
import os
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin

CURRENT_YEAR = "2026"

def get_column_by_substring(df, substrings):
    for sub in substrings:
        for i, col in enumerate(df.columns):
            if sub.lower() in str(col).lower():
                return i
    return None

def parse_driver_name(raw_name):
    clean_name = str(raw_name).replace('\u00a0', ' ').strip()
    name_parts = clean_name.split(' ')
    name_parts = [p for p in name_parts if p]
    
    if not name_parts:
        return "", "", "UNK"
        
    code = name_parts[-1]
    given_name = name_parts[0]
    family_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else (name_parts[1] if len(name_parts) == 2 else "")
    
    if len(code) > 3 and code[-3:].isupper():
        actual_code = code[-3:]
        family_name = family_name + " " + code[:-3] if family_name else code[:-3]
        code = actual_code

    return given_name.strip(), family_name.strip(), code.strip()

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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(master_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        race_paths = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"/{CURRENT_YEAR}/races/" in href and ("race-result" in href or "result.html" in href):
                full_url = urljoin(master_url, href)
                race_paths.append(full_url)
                
        race_paths = list(dict.fromkeys(race_paths))
        print(f"Found {len(race_paths)} valid {CURRENT_YEAR} race links to scan.")
        
        races_list = []
        for detail_url in race_paths:
            try:
                detail_tables = pd.read_html(detail_url)
                if not detail_tables:
                    continue
                
                race_df = None
                for table in detail_tables:
                    p_idx = get_column_by_substring(table, ['pos', 'position'])
                    if p_idx is not None and len(table) > 0:
                        first_val = str(table.iloc[0, p_idx]).strip()
                        if first_val == "1":
                            race_df = table
                            break
                
                if race_df is None:
                    race_df = detail_tables[0]
                
                pos_idx = get_column_by_substring(race_df, ['pos', 'position']) or 1
                driver_idx = get_column_by_substring(race_df, ['driver', 'name']) or 2
                
                if len(race_df) == 0 or "no results available" in str(race_df.iloc[0]).lower():
                    continue

                segments = detail_url.split('/')
                slug_idx = -2 if segments[-1].endswith('.html') and 'race-result' in segments[-1] else -1
                gp_slug = segments[slug_idx].replace('-', ' ').title()
                
                if not gp_slug or gp_slug.isdigit() or gp_slug.lower() in ['race result', 'race-result']:
                    gp_slug = segments[slug_idx - 1].replace('-', ' ').title()
                
                gp_name = gp_slug if "grand prix" in gp_slug.lower() else f"{gp_slug} Grand Prix"
                if "Usa" in gp_name: gp_name = gp_name.replace("Usa", "United States")
                
                podium_results = []
                for i in range(min(3, len(race_df))):
                    row = race_df.iloc[i]
                    p_val = str(row.iloc[pos_idx]).strip()
                    
                    if not p_val.isdigit():
                        continue
                        
                    given_name, family_name, code = parse_driver_name(row.iloc[driver_idx])
                    
                    podium_results.append({
                        "position": p_val,
                        "Driver": {
                            "givenName": given_name,
                            "familyName": family_name,
                            "code": code
                        }
                    })
                
                if podium_results:
                    races_list.append({
                        "raceName": gp_name,
                        "Results": podium_results
                    })
            except Exception as item_err:
                print(f"⚠️ Skipping item table processing mismatch: {item_err}")
                continue

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

def generate_clean_calendar():
    print("Generating Complete 2026 Calendar...")
    
    # Complete 24-Round Master Calendar Data Mapping for your Dashboard
    races_list = [
        {"round": "1", "raceName": "Australian Grand Prix", "date": "2026-03-08", "time": "04:00:00Z", "Circuit": {"circuitName": "Albert Park Circuit"}},
        {"round": "2", "raceName": "Chinese Grand Prix", "date": "2026-03-15", "time": "07:00:00Z", "Circuit": {"circuitName": "Shanghai International Circuit"}},
        {"round": "3", "raceName": "Japanese Grand Prix", "date": "2026-03-29", "time": "05:00:00Z", "Circuit": {"circuitName": "Suzuka International Racing Course"}},
        {"round": "4", "raceName": "Bahrain Grand Prix", "date": "2026-04-12", "time": "15:00:00Z", "Circuit": {"circuitName": "Bahrain International Circuit"}},
        {"round": "5", "raceName": "Saudi Arabian Grand Prix", "date": "2026-04-19", "time": "17:00:00Z", "Circuit": {"circuitName": "Jeddah Corniche Circuit"}},
        {"round": "6", "raceName": "Miami Grand Prix", "date": "2026-05-03", "time": "20:00:00Z", "Circuit": {"circuitName": "Miami International Autodrome"}},
        {"round": "7", "raceName": "Canadian Grand Prix", "date": "2026-05-24", "time": "18:00:00Z", "Circuit": {"circuitName": "Circuit Gilles-Villeneuve"}},
        {"round": "8", "raceName": "Monaco Grand Prix", "date": "2026-06-07", "time": "13:00:00Z", "Circuit": {"circuitName": "Circuit de Monaco"}},
        {"round": "9", "raceName": "Barcelona-Catalunya Grand Prix", "date": "2026-06-14", "time": "13:00:00Z", "Circuit": {"circuitName": "Circuit de Barcelona-Catalunya"}},
        {"round": "10", "raceName": "Austrian Grand Prix", "date": "2026-06-28", "time": "13:00:00Z", "Circuit": {"circuitName": "Red Bull Ring"}},
        {"round": "11", "raceName": "British Grand Prix", "date": "2026-07-05", "time": "14:00:00Z", "Circuit": {"circuitName": "Silverstone Circuit"}},
        {"round": "12", "raceName": "Belgian Grand Prix", "date": "2026-07-19", "time": "13:00:00Z", "Circuit": {"circuitName": "Circuit de Spa-Francorchamps"}},
        {"round": "13", "raceName": "Hungarian Grand Prix", "date": "2026-07-26", "time": "13:00:00Z", "Circuit": {"circuitName": "Hungaroring"}},
        {"round": "14", "raceName": "Dutch Grand Prix", "date": "2026-08-23", "time": "13:00:00Z", "Circuit": {"circuitName": "Circuit Zandvoort"}},
        {"round": "15", "raceName": "Italian Grand Prix", "date": "2026-09-06", "time": "13:00:00Z", "Circuit": {"circuitName": "Autodromo Nazionale Monza"}},
        {"round": "16", "raceName": "Spanish Grand Prix", "date": "2026-09-13", "time": "13:00:00Z", "Circuit": {"circuitName": "Madrid Street Circuit"}},
        {"round": "17", "raceName": "Azerbaijan Grand Prix", "date": "2026-09-26", "time": "11:00:00Z", "Circuit": {"circuitName": "Baku City Circuit"}},
        {"round": "18", "raceName": "Singapore Grand Prix", "date": "2026-10-11", "time": "12:00:00Z", "Circuit": {"circuitName": "Marina Bay Street Circuit"}},
        {"round": "19", "raceName": "United States Grand Prix", "date": "2026-10-25", "time": "19:00:00Z", "Circuit": {"circuitName": "Circuit of The Americas"}},
        {"round": "20", "raceName": "Mexico City Grand Prix", "date": "2026-11-01", "time": "20:00:00Z", "Circuit": {"circuitName": "Autódromo Hermanos Rodríguez"}},
        {"round": "21", "raceName": "São Paulo Grand Prix", "date": "2026-11-08", "time": "17:00:00Z", "Circuit": {"circuitName": "Autódromo José Carlos Pace"}},
        {"round": "22", "raceName": "Las Vegas Grand Prix", "date": "2026-11-21", "time": "06:00:00Z", "Circuit": {"circuitName": "Las Vegas Strip Circuit"}},
        {"round": "23", "raceName": "Qatar Grand Prix", "date": "2026-11-29", "time": "17:00:00Z", "Circuit": {"circuitName": "Lusail International Circuit"}},
        {"round": "24", "raceName": "Abu Dhabi Grand Prix", "date": "2026-12-06", "time": "13:00:00Z", "Circuit": {"circuitName": "Yas Marina Circuit"}}
    ]

    ergast_json = {
        "MRData": {
            "RaceTable": {
                "season": CURRENT_YEAR,
                "Races": races_list
            }
        }
    }

    os.makedirs("api", exist_ok=True)
    with open("api/current.json", "w", encoding="utf-8") as f:
        json.dump(ergast_json, f, indent=2)
    print("✅ Complete 24-Round Calendar setup finalized.")

    os.makedirs("api", exist_ok=True)
    with open("api/current.json", "w", encoding="utf-8") as f:
        json.dump(ergast_json, f, indent=2)
    print("✅ Pristine Calendar setup complete.")

if __name__ == "__main__":
    try:
        scrape_standings()
        scrape_race_results()
        generate_clean_calendar()
        print("🚀 API generation completed successfully!")
    except Exception as main_error:
        print(f"💥 Critical API build failure: {main_error}")
        sys.exit(1)
