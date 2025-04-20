from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import json
import os
from datetime import datetime

# LangChain Core
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document

# LangChain Chains
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# LangChain Community / Vectorstores
from langchain_community.vectorstores import FAISS
from pymongo import MongoClient
from bson import ObjectId

# Google Generative AI
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

app = Flask(__name__)
CORS(app)
client = MongoClient("mongodb+srv://gungunpathak600:4d1Hy0OmIAdICa69@ragasha.8mnsjsh.mongodb.net/?retryWrites=true&w=majority&appName=ragAsha")
db = client["ragAsha"]
conversations_collection = db["conversations"]

# ---- Load documents from JSON ----

# ---- Load documents from JSON ----

def load_documents_from_json():
    docs = []

    # Load event data
    with open('utils_remove/event_data.json', 'r', encoding='utf-8') as f:
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
    with open('utils_remove/linkedin_jobs.json', 'r', encoding='utf-8') as f:
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
    with open('utils_remove/tech_news.json', 'r', encoding='utf-8') as f:
        tech_news = json.load(f)["data"]
        for article in tech_news:
            content = f"""Title: {article.get("title", "")}
Summary: {article.get("snippet", "")}
Published At: {article.get("published_datetime_utc", "")}
Source: {article.get("source_name", "")}
Link: {article.get("link", "")}"""
            docs.append(Document(page_content=content))

    return docs


# ---- Initialize RAG ----

def initialize_rag_system():
    print("🔧 Initializing RAG system with real data...")
    start_time = time.time()

    docs = load_documents_from_json()

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

# ---- RAG instance (only once) ----

rag_chain = initialize_rag_system()

# ---- Simple NLP Bias Detection ----

# ---- Simple NLP Bias Detection ----

def nlp_based_bias_detector(text):
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

# ---- Gemini-based Bias Detection ----

def gemini_bias_detector(text):
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    prompt = f"""
You are a bias detection assistant. Analyze the following text and tell if it's biased or neutral. 
Explain the reason in 2-3 lines.

Text:
{text}
    """
    response = model.invoke(prompt)
    return response.content.strip()


# Convert chat history to serialized format for MongoDB
def serialize_messages(messages):
    serialized = []
    for msg in messages:
        serialized.append({
            "type": msg.type,
            "content": msg.content
        })
    return serialized

# Convert stored messages back to langchain format
from langchain_core.messages import AIMessage, HumanMessage

def deserialize_messages(messages):
    deserialized = []
    for msg in messages:
        if msg['type'] == 'human':
            deserialized.append(HumanMessage(content=msg['content']))
        elif msg['type'] == 'ai':
            deserialized.append(AIMessage(content=msg['content']))
    return deserialized



# ---- Flask Endpoint ----

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        question = data.get("question", "")
        conversation_id = data.get("conversation_id")

        if not question:
            return jsonify({"error": "No question provided."}), 400

        # ---- Fetch or initialize conversation ----
        if conversation_id:
            try:
                conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
                if not conversation:
                    return jsonify({'error': 'Conversation not found'}), 404
                chat_history = deserialize_messages(conversation['messages'])
            except:
                return jsonify({'error': 'Invalid conversation ID'}), 400
        else:
            chat_history = []
            conversation = {
                'messages': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            result = conversations_collection.insert_one(conversation)
            conversation_id = str(result.inserted_id)

        # ---- NLP and Gemini Bias Detection ----
        nlp_result = nlp_based_bias_detector(question)
        gemini_result = gemini_bias_detector(question)

        # ---- RAG Processing ----
        inputs = {
            "input": question,
            "chat_history": chat_history
        }
        result = rag_chain.invoke(inputs)
        answer = result["answer"]

        # ---- Append to chat history ----
        chat_history.append(HumanMessage(content=question))
        chat_history.append(AIMessage(content=answer))
        updated_messages = serialize_messages(chat_history)

        # ---- Update MongoDB ----
        conversations_collection.update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {
                'messages': updated_messages,
                'updated_at': datetime.now().isoformat()
            }}
        )

        return jsonify({
            "bias_analysis": {
                "nlp_based": nlp_result,
                "gemini_based": gemini_result
            },
            "response": answer,
            "conversation_id": conversation_id,
            "messages": updated_messages
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




@app.route('/conversations', methods=['GET'])
def get_conversations():
    conversations = list(conversations_collection.find({}, {'messages': 0}).sort('updated_at', -1).limit(20))
    for conv in conversations:
        conv['_id'] = str(conv['_id'])
    return jsonify(conversations)

# ======= Get Specific Conversation =======

@app.route('/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    try:
        conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        conversation['_id'] = str(conversation['_id'])
        return jsonify(conversation)
    except:
        return jsonify({'error': 'Invalid conversation ID'}), 400

# ======= Delete Specific Conversation =======

@app.route('/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    try:
        result = conversations_collection.delete_one({'_id': ObjectId(conversation_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Conversation not found'}), 404
        return jsonify({'status': 'success'})
    except:
        return jsonify({'error': 'Invalid conversation ID'}), 400


# ---- Start Server ----

if __name__ == "__main__":
    print("🚀 Starting Flask server...")
    app.run(debug=True)