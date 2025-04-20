from langchain_google_genai import ChatGoogleGenerativeAI


def nlp_based_bias_detector(text):
    """Detect bias in text using NLP-based methods"""
    biased_keywords = [
        "always", "never", "everyone knows", "clearly", "obviously", "undoubtedly", 
        "no one can deny", "proven", "worst", "best", "superior", "inferior", 
        "fail", "success", "disaster", "genius"
    ]
    bias_hits = [word for word in biased_keywords if word.lower() in text.lower()]
    is_biased = len(bias_hits) > 0

    return {
        "biased": is_biased,
        "trigger_words": bias_hits,
        "message": "Biased terms detected." if is_biased else "No clear bias found using NLP-based method."
    }


def gemini_bias_detector(text):
    """Detect bias in text using Gemini AI model"""
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    prompt = f"""
You are a bias detection assistant. Analyze the following text and tell if it's biased or neutral. 
Explain the reason in 2-3 lines.

Text:
{text}
    """
    response = model.invoke(prompt)
    return response.content.strip()
