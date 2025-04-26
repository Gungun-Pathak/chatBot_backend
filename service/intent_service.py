import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI

def detect_intent_and_data(user_input):
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)

    prompt = f"""
You are an intelligent assistant that classifies user intent and extracts structured data.
Return *only* a strict JSON object in the format below. DO NOT add any explanation.

Expected format:
{{
  "intent": "signup" | "update_profile" | "general",
  "data": {{
    "name": string | null,
    "email": string | null,
    "phone": string | null,
    "skills": [string] | [],
    "bio": string | null
  }}
}}

Analyze this text and return the result in the format above:
\"\"\"{user_input}\"\"\"
"""

    response = model.invoke(prompt)

    # Extract JSON safely using regex
    try:
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            raise ValueError("No JSON found")
    except Exception:
        return {
            "intent": "general",
            "data": {
                "name": None,
                "email": None,
                "phone": None,
                "skills": [],
                "bio": None
            }
        }