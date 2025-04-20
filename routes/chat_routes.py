from flask import Blueprint, request, jsonify
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime

from config import conversations_collection
from service.rag_service import initialize_rag_system
from utils.serialization import serialize_messages, deserialize_messages
from service.bias_service import nlp_based_bias_detector, gemini_bias_detector
from service.intent_service import detect_intent_and_data  # New import
from langchain_core.messages import HumanMessage, AIMessage

chat_bp = Blueprint('chat', __name__)
CORS(chat_bp)

rag_chain = initialize_rag_system()

@chat_bp.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question")
    conversation_id = data.get("conversation_id")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        # Check if the user intends to sign up or update profile
        intent_result = detect_intent_and_data(question)
        intent_type = intent_result.get("intent")
        extracted_data = intent_result.get("data", {})

        if intent_type in ["signup", "update_profile"]:
            return jsonify({
                "intent": intent_type,
                "extracted_data": extracted_data,
                "message": f"Intent identified as {intent_type.replace('_', ' ').title()}",
                "conversation_id": conversation_id  # could be None if new
            })

        # Proceed with regular RAG-based answer generation
        if conversation_id:
            conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            chat_history = deserialize_messages(conversation['messages'])
        else:
            chat_history = []
            conversation = {
                'messages': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            result = conversations_collection.insert_one(conversation)
            conversation_id = str(result.inserted_id)

        # Run bias detection
        nlp_result = nlp_based_bias_detector(question)
        gemini_result = gemini_bias_detector(question)

        # Get RAG response
        result = rag_chain.invoke({"input": question, "chat_history": chat_history})
        answer = result["answer"]

        chat_history += [HumanMessage(content=question), AIMessage(content=answer)]
        updated = serialize_messages(chat_history)

        conversations_collection.update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {'messages': updated, 'updated_at': datetime.now().isoformat()}}
        )

        return jsonify({
            "bias_analysis": {
                "nlp_based": nlp_result,
                "gemini_based": gemini_result
            },
            "response": answer,
            "conversation_id": conversation_id,
            "messages": updated,
            "intent": "general"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
