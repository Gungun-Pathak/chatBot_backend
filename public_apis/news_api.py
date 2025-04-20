import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_or_load_news_data(live_mode=False, file_path="tech_news.json"):
    """
    Fetch news from API if live_mode=True, else load from saved JSON file.
    """
    if not live_mode and os.path.exists(file_path):
        print(f"Loading news data from local file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("Making API call to fetch real-time tech news...")

    url = "https://real-time-news-data.p.rapidapi.com/topic-news-by-section"
    querystring = {
        "topic": "TECHNOLOGY",
        "section": "CAQiSkNCQVNNUW9JTDIwdk1EZGpNWFlTQldWdUxVZENHZ0pKVENJT0NBUWFDZ29JTDIwdk1ETnliSFFxQ2hJSUwyMHZNRE55YkhRb0FBKi4IACoqCAoiJENCQVNGUW9JTDIwdk1EZGpNWFlTQldWdUxVZENHZ0pKVENnQVABUAE",
        "limit": "500",
        "country": "IN",
        "lang": "en"
    }

    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "real-time-news-data.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code == 200:
            data = response.json()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Tech news data saved to {file_path}")
            return data
        else:
            raise Exception(f"API call failed: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
        return None


# Example usage
if __name__ == "__main__":
    # Set live_mode=True for the first time only to save the API response
    news_data = fetch_or_load_news_data(live_mode=False)
    if news_data:
        print(f"News items received: {len(news_data.get('data', [])) if 'data' in news_data else 'Unknown format'}")
