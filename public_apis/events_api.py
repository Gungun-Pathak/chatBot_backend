import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# File path to save the API data
FILE_PATH = "event_data.json"

def fetch_and_save_events_data(live_mode=False):
    """
    Fetch tech event data from API if live_mode is True,
    else load from saved JSON file.
    """
    if not live_mode and os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as file:
            print("🔁 Loaded data from saved JSON file.")
            return json.load(file)

    print("🌐 Fetching data from API...")
    url = "https://real-time-events-search.p.rapidapi.com/search-events"
    querystring = {
        "query": "Technology events in india",
        "date": "any",
        "is_virtual": "false",
        "start": "0"
    }

    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "real-time-events-search.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        data = response.json()
        with open(FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        print(f"✅ Data saved to {FILE_PATH}")
        return data
    else:
        raise Exception(f"API call failed: {response.status_code} - {response.text}")

# Example usage (set live_mode=True only once during development)
if __name__ == "__main__":
    data = fetch_and_save_events_data(live_mode=True)  # change to False after first run
    print(f"📦 Total events fetched: {len(data.get('results', []))}")
