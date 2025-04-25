import fitz  # PyMuPDF
import re  # Regular expressions
import json  # JSON parsing
from service.gemini_service import gemini_prompt_response

def extract_text_from_resume(pdf_file) -> str:
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()

def analyze_resume(text: str) -> dict:
    prompt = f"""
You are an AI career mentor. Analyze the following resume content:

{text}

Based on the resume, provide:
1. Key skills
2. Online course recommendations
3. A 3-step career roadmap
4. Resume shortcomings
5. Tips for improvement

Respond in structured JSON like:
{{
  "skills": [...],
  "recommended_courses": [...],
  "career_roadmap": [...],
  "shortcomings": [...],
  "improvement_tips": [...]
}}
    """
    response = gemini_prompt_response(prompt)

    # Remove Markdown-style code block (```json ... ```)
    cleaned = re.sub(r"```json|```", "", response).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_response": cleaned}
