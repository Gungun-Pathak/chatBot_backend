import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_or_load_upwork_data(live_mode=False, file_path="upwork_jobs.json"):
    if not live_mode and os.path.exists(file_path):
        print(f"Loading data from local file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("Making API call to fetch Upwork job data...")

    url = "https://upwork-jobs-api2.p.rapidapi.com/active-freelance-1h"
    querystring = {
        "location_filter": "India",
        
        
       
    }

    headers = {
 "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host":"upwork-jobs-api2.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code == 200:
            data = response.json()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Upwork job data saved to {file_path}")
            return data
        else:
            print(f"Headers used: {headers}")
            print(f"Querystring: {querystring}")
            raise Exception(f"API call failed: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
        return None


# Example usage
if __name__ == "__main__":
    data = fetch_or_load_upwork_data(live_mode=True)
    if data:
        print(f"Jobs received: {len(data.get('jobs', [])) if 'jobs' in data else 'Unknown format'}")
