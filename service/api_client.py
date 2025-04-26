import os
import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

def fetch_realtime_data(source):
    """Conditional API fetcher"""
    if os.getenv("APP_MODE", "development") != "production":
        return []

    endpoints = {
        "events": {
            "url": "https://real-time-events-search.p.rapidapi.com/search-events",
            "headers": {"x-rapidapi-key": os.getenv("RAPIDAPI_KEY")},
            "params": {"query": "Technology events in india"}
        },
        "jobs": {
            "url": "https://api.scrapingdog.com/linkedinjobs",
            "params": {"api_key": os.getenv("SCRAPINGDOG_API_KEY")}
        },
        "news": {
            "url": "https://real-time-news-data.p.rapidapi.com/topic-news-by-section",
            "headers": {"x-rapidapi-key": os.getenv("RAPIDAPI_KEY")},
            "params": {"topic": "TECHNOLOGY"}
        }
    }

    try:
        config = endpoints[source]
        response = requests.get(
            config["url"],
            headers=config.get("headers", {}),
            params=config["params"],
            timeout=10
        )
        return response.json().get("data" if source != "jobs" else "jobs", [])
    except Exception as e:
        print(f"API Error ({source}): {str(e)}")
        return []

def fetch_realtime_sources(sources):
    """Fetch only required sources"""
    with ThreadPoolExecutor() as executor:
        return {source: fetch_realtime_data(source) for source in sources}