import os
from flask import Blueprint, request, jsonify, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
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

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# Blueprint for voice-related routes
voice_bp = Blueprint('voice', __name__)
rag_chain = initialize_rag_system()

# Twilio client setup
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)


@voice_bp.route("/make_call", methods=["GET"])
def make_call():
    to_phone_number = request.args.get('to')  # Phone number to call
    from_phone_number = "+15675571541" # Your Twilio phone number
    if not to_phone_number:
        return "Please provide the 'to' phone number as a query parameter.", 400

    # Initiate call
    call = client.calls.create(
        url="https://ashaai-backend.onrender.com/voice/voice",  # URL for the TwiML response
        to=to_phone_number,
        from_=from_phone_number
    )
    return f"Call initiated. SID: {call.sid}"


@voice_bp.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()

    # Create new conversation at call start
    new_chat = [SystemMessage(content="You are a helpful voice assistant for women's career support.")]
    inserted = conversations_collection.insert_one({
        "messages": serialize_messages(new_chat),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    conversation_id = str(inserted.inserted_id)

    # Build URLs with conversation_id
    action_url = f"https://ashaai-backend.onrender.com/voice/handle_recording?conversation_id={conversation_id}"
    transcribe_callback_url = f"https://ashaai-backend.onrender.com/voice/handle_transcription?conversation_id={conversation_id}"

    response.say("Hello! Please ask your question, and I will assist you.")
    response.record(
        action=action_url,
        max_length=30,
        transcribe=True,
        transcribe_callback=transcribe_callback_url
    )
    return Response(str(response), mimetype='application/xml')

@voice_bp.route("/handle_transcription", methods=["POST"])
def handle_transcription():
    transcription = request.form['TranscriptionText']
    conversation_id = request.args.get('conversation_id')  # From URL params

    # Load conversation using conversation_id
    try:
        conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
        chat_history = deserialize_messages(conversation['messages'])
    except Exception as e:
        return Response(str(VoiceResponse().say("Error processing request")), mimetype='application/xml')

    # Intent detection
    intent_result = detect_intent_and_data(transcription)
    intent_type = intent_result.get("intent")

    if intent_type in ["signup", "update_profile"]:
        response = VoiceResponse()
        response.say(f"Received your request for {intent_type.replace('_', ' ')}. Please provide more details.")
        return Response(str(response), mimetype='application/xml')


    # Detect sentiment and check if uplifting message is needed
    sentiment = detect_sentiment(transcription)
    received_empowering_response = any(
        isinstance(msg, AIMessage) and "believing in yourself" in msg.content.lower()
        for msg in chat_history
    )

    if sentiment == "negative" and not received_empowering_response:
        empowering_message = get_empowering_response(topic="women empowerment")
        chat_history += [HumanMessage(content=transcription), AIMessage(content=empowering_message)]
        updated = serialize_messages(chat_history)

        conversations_collection.update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {'messages': updated, 'updated_at': datetime.now().isoformat()}}
        )

        response = VoiceResponse()
        response.say(empowering_message)
        return Response(str(response), mimetype='application/xml')

    # Bias detection
    nlp_result = nlp_based_bias_detector(transcription)
    gemini_result = gemini_bias_detector(transcription)

    # RAG-based response
    result = rag_chain.invoke({"input": transcription, "chat_history": chat_history})
    answer = result["answer"]

    # Update chat history and database
    chat_history += [HumanMessage(content=transcription), AIMessage(content=answer)]
    conversations_collection.update_one(
        {'_id': ObjectId(conversation_id)},
        {'$set': {'messages': serialize_messages(chat_history), 'updated_at': datetime.now().isoformat()}}
    )

    # Return TwiML response
    response = VoiceResponse()
    response.say(answer)
    return Response(str(response), mimetype='application/xml')

@voice_bp.route("/handle_recording", methods=["POST"])
def handle_recording():
    recording_url = request.form['RecordingUrl']
    conversation_id = request.args.get('conversation_id')

    # Optionally save recording URL to conversation
    if conversation_id:
        conversations_collection.update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {'recording_url': recording_url}}
        )

    # Return empty TwiML to keep the line open (or process further)
    response = VoiceResponse()
    return Response(str(response), mimetype='application/xml')


# If required, you can add other routes here for handling more functionalities
