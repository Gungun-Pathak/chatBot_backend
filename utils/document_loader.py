import json
from langchain_core.documents import Document


def load_documents_from_json():
    """Load documents from JSON files into LangChain format"""
    docs = []

    # Load event data
    with open('data/event_data.json', 'r', encoding='utf-8') as f:
        events = json.load(f)["data"]
        for event in events:
            content = f"""Event: {event.get("name", "")}
Date: {event.get("date_human_readable", "")}
Venue: {event.get("venue", {}).get("full_address", "")}
Virtual: {event.get("is_virtual", False)}
Link: {event.get("link", "")}
Description: {event.get("description", "")}"""
            docs.append(Document(page_content=content))

    # Load LinkedIn jobs
    with open('data/linkedin_jobs.json', 'r', encoding='utf-8') as f:
        job_list = json.load(f)
        if isinstance(job_list, list):  # Ensure it's a list
            for job in job_list:
                content = f"""Job Position: {job.get("job_position", "")}
Company: {job.get("company_name", "")}
Location: {job.get("job_location", "")}
Posted On: {job.get("job_posting_date", "")}
Apply Link: {job.get("job_link", "")}"""
                docs.append(Document(page_content=content))
        else:
            print("Error: 'linkedin_jobs.json' is not a list!")

    # Load tech news
    with open('data/tech_news.json', 'r', encoding='utf-8') as f:
        tech_news = json.load(f)["data"]
        for article in tech_news:
            content = f"""Title: {article.get("title", "")}
Summary: {article.get("snippet", "")}
Published At: {article.get("published_datetime_utc", "")}
Source: {article.get("source_name", "")}
Link: {article.get("link", "")}"""
            docs.append(Document(page_content=content))

    return docs
