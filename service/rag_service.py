import time
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from utils.document_loader import load_documents_from_pdf


def initialize_rag_system():
    """Initialize the RAG system with real data"""
    print("🔧 Initializing RAG system with real data...")
    start_time = time.time()

    docs = load_documents_from_pdf()

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(docs, embedding=embeddings)
    retriever = vectorstore.as_retriever()

    # LLM setup
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)

    # Rephrasing prompt
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given chat history and a new user question, rephrase it as a standalone question."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])
    history_aware_retriever = create_history_aware_retriever(model, retriever, contextualize_q_prompt)

    # QA prompt (corrected version)
    qa_prompt =ChatPromptTemplate.from_messages([
    ("system", """For event, job, or news-related queries, ALWAYS respond with JSON using this structure and only from context provided:

For Event Queries:
{{
    "summary": "Brief overview",
    "sections": [
        {{
            "title": "Event Details",
            "content": [
                "Dates: [event_dates]",
                "Location: [venue]",
                "Type: [event_type]",
                "Focus: [topics]"
            ],
            "icon": "calendar"
        }}
    ],
    "links": [
        {{
            "text": "Official Website",
            "url": "[event_url]",
            "type": "event"
        }}
    ],
    "actions": [
        {{
            "type": "register",
            "text": "Register Now",
            "url": "[registration_url]"
        }}
    ]
}}

For Job Queries:
{{
    "summary": "Brief overview",
    "sections": [
        {{
            "title": "Job Details",
            "content": [
                "Position: [job_title]",
                "Company: [company_name]",
                "Location: [job_location]",
                "Posted: [posted_date]",
                "Focus: [skills_focus]"
            ],
            "icon": "briefcase"
        }}
    ],
    "links": [
        {{
            "text": "Company Careers Page",
            "url": "[company_career_url]",
            "type": "career"
        }}
    ],
    "actions": [
        {{
            "type": "apply",
            "text": "Apply Now",
            "url": "[application_url]"
        }}
    ]
}}

For News Queries:
{{
    "summary": "[news_title]",
    "sections": [
        {{
            "title": "News Details",
            "content": [
                "Title: [news_title]",
                "Date: [news_date]",
                "Source: [news_source]",
                "Highlights: [description or important points]"
            ],
            "icon": "newspaper"
        }}
    ],
    "links": [
        {{
            "text": "Read Full Article",
            "url": "[article_url]",
            "type": "news"
        }}
    ]
}}

Special Instructions for JobsForHer Foundation:
- If the user query asks about **jobs** at **JobsForHer Foundation**, DO NOT provide job-related JSON.
- Instead, retrieve  information about JobsForHer Foundation based ONLY on the context.
- Format the response in this structure:
    
    {{
        "summary": "JobsForHer Foundation Overview",
        "sections": [
            {{
                "title": "Foundation Details",
                "content": [
                    "Mission: [mission_statement]",
                    "Focus: [focus_areas]",
                    "Programs: [programs_offered]"
                ],
                "icon": "foundation"
            }}
        ],
        "links": [
            {{
                "text": "Foundation Website",
                "url": "[foundation_url]",
                "type": "foundation"
            }}
        ]
    }}
- If the user asks any other question about JobsForHer Foundation (not job-related), also answer based ONLY on context and using the same structure.

IMPORTANT RULES:
- Only use information strictly from the provided context.
- Never invent or assume missing information.


Context: {context}
    """),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])
    question_answer_chain = create_stuff_documents_chain(model, qa_prompt)
    
    # Final RAG chain
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    print(f"✅ RAG ready in {time.time() - start_time:.2f} seconds with {len(docs)} documents.")
    return rag_chain