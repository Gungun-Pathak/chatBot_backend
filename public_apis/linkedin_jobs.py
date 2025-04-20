import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_or_load_linkedin_jobs(live_mode=False, file_path="linkedin_jobs.json"):
    """
    Fetch LinkedIn jobs using ScrapingDog API if live_mode=True,
    else load from saved JSON file.
    """
    if not live_mode and os.path.exists(file_path):
        print(f"Loading LinkedIn job data from local file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("Making API call to fetch LinkedIn job data...")

    api_key = os.getenv("SCRAPINGDOG_API_KEY")
    url = "https://api.scrapingdog.com/linkedinjobs"

    params = {
        "api_key": api_key,
        "field": "software developer",  # example: 'software developer'
        "geoid": "102713980",  # LinkedIn location id (optional)
        "page": 1,
        "sortBy": "",  # 'recent', 'relevance' (if supported)
        "jobType": "",  # 'F', 'P' for full-time, part-time
        "expLevel": "",  # '1', '2' etc.
        "workType": "",  # 'remote', 'onsite', etc.
        "filterByCompany": ""  # company name if any
    }

    try:
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"LinkedIn jobs data saved to {file_path}")
            return data
        else:
            raise Exception(f"API call failed: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
        return None


# Example usage
if __name__ == "__main__":
    linkedin_data = fetch_or_load_linkedin_jobs(live_mode=False)
    if linkedin_data:
        print(f"Jobs fetched: {len(linkedin_data.get('jobs', [])) if 'jobs' in linkedin_data else 'Unknown format'}")
