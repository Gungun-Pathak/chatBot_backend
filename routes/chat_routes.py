from flask import Blueprint, request, jsonify
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime

from config import conversations_collection
from service.rag_service import initialize_rag_system
from utils.serialization import serialize_messages, deserialize_messages
from service.bias_service import nlp_based_bias_detector, gemini_bias_detector
from service.intent_service import detect_intent_and_data
from service.sentiment_service import detect_sentiment
from service.gemini_service import get_empowering_response

from langchain_core.messages import HumanMessage, AIMessage


chat_bp = Blueprint('chat', __name__)
rag_chain = initialize_rag_system()


@chat_bp.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question")
    conversation_id = data.get("conversation_id")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        # Intent detection (e.g., signup, update_profile)
        intent_result = detect_intent_and_data(question)
        intent_type = intent_result.get("intent")
        extracted_data = intent_result.get("data", {})

        if intent_type in ["signup", "update_profile"]:
            return jsonify({
                "intent": intent_type,
                "extracted_data": extracted_data,
                "message": f"Intent identified as {intent_type.replace('_', ' ').title()}",
                "conversation_id": conversation_id
            })

        # Load or create chat history
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

        # Detect sentiment and check if uplifting message is needed
        sentiment = detect_sentiment(question)
        received_empowering_response = any(
            isinstance(msg, AIMessage) and "believing in yourself" in msg.content.lower()
            for msg in chat_history
        )

        if sentiment == "negative" and not received_empowering_response:
            empowering_message = get_empowering_response(topic="women empowerment")
            chat_history += [HumanMessage(content=question), AIMessage(content=empowering_message)]
            updated = serialize_messages(chat_history)

            conversations_collection.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$set': {'messages': updated, 'updated_at': datetime.now().isoformat()}}
            )

            return jsonify({
                "response": empowering_message,
                "conversation_id": conversation_id,
                "sentiment": sentiment,
                "intent": "uplift"
            })
        print(f"Detected Sentiment: {sentiment}")


        # Bias detection
        nlp_result = nlp_based_bias_detector(question)
        gemini_result = gemini_bias_detector(question)

        # RAG-based response
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
