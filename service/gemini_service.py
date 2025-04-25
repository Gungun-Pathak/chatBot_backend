from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize Gemini LLM once (you can reuse it)
gemini_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)

def get_empowering_response(topic="women empowerment") -> str:
    """
    Get an empowering or motivational response from Gemini based on a given topic.
    Ideal for uplifting users when low sentiment is detected.
    """
    prompt = (
        f"Share a real, short, and inspiring story or message on the topic of {topic}. "
        "Make sure it feels personal and motivational for a woman who might be feeling low, "
        "underconfident, or demotivated."
    )
    response = gemini_model.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)

def gemini_prompt_response(prompt: str) -> str:
    """
    General-purpose Gemini LLM prompt function.
    """
    response = gemini_model.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)