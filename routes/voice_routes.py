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

from langchain_core.messages import HumanMessage, AIMessage


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
    """Handles incoming voice calls and starts recording for speech-to-text."""
    response = VoiceResponse()

    # Gather speech input (Twilio will transcribe the audio)
    response.say("Hello! Please ask your question, and I will assist you.")
    response.record(
        action="https://ashaai-backend.onrender.com/voice/handle_recording",  # This is where the recording is processed
        max_length=30,  # 30 seconds to speak
        transcribe=True,  # Automatically transcribe speech to text
        transcribe_callback="https://ashaai-backend.onrender.com/voice/handle_transcription"  # URL to handle transcription result
    )
    return Response(str(response), mimetype='application/xml')


@voice_bp.route("/handle_transcription", methods=["POST"])
def handle_transcription():
    """Handles transcription result from Twilio."""
    transcription = request.form['TranscriptionText']
    print(f"Transcription: {transcription}")

    conversation_id = request.args.get('conversation_id', None)
    chat_history = []

    if conversation_id:
        conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
        if conversation:
            chat_history = deserialize_messages(conversation['messages'])

    # Intent detection
    intent_result = detect_intent_and_data(transcription)
    intent_type = intent_result.get("intent")
    extracted_data = intent_result.get("data", {})

    if intent_type in ["signup", "update_profile"]:
        return jsonify({
            "intent": intent_type,
            "extracted_data": extracted_data,
            "message": f"Intent identified as {intent_type.replace('_', ' ').title()}",
            "conversation_id": conversation_id
        })

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

    chat_history += [HumanMessage(content=transcription), AIMessage(content=answer)]
    updated = serialize_messages(chat_history)

    conversations_collection.update_one(
        {'_id': ObjectId(conversation_id)},
        {'$set': {'messages': updated, 'updated_at': datetime.now().isoformat()}}
    )

    response = VoiceResponse()
    response.say(answer)

    return Response(str(response), mimetype='application/xml')


@voice_bp.route("/handle_recording", methods=["POST"])
def handle_recording():
    """Handles the audio recording of the call and processes it further."""
    recording_url = request.form['RecordingUrl']
    print(f"Recording URL: {recording_url}")

    # Further processing or storage of the recording can be done here
    return jsonify({"status": "success", "recording_url": recording_url})


# If required, you can add other routes here for handling more functionalities
