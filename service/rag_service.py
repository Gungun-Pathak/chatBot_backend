import time
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from utils.document_loader import load_documents_from_json_and_pdf


def initialize_rag_system():
    """Initialize the RAG system with real data"""
    print("🔧 Initializing RAG system with real data...")
    start_time = time.time()

    docs = load_documents_from_json_and_pdf()

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

    # QA prompt
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an assistant answering based on the provided context:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])
    question_answer_chain = create_stuff_documents_chain(model, qa_prompt)

    # Final RAG chain
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    print(f"✅ RAG ready in {time.time() - start_time:.2f} seconds with {len(docs)} documents.")
    return rag_chain
