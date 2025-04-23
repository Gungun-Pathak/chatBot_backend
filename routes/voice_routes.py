import os
from flask import Blueprint, request, Response, url_for, jsonify
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
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
import phonenumbers

voice_bp = Blueprint('voice', __name__)
rag_chain = initialize_rag_system()
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

def validate_phone_number(number):
    try:
        parsed = phonenumbers.parse(number, None)
        return phonenumbers.is_valid_number(parsed)
    except:
        return False

def create_new_conversation():
    new_chat = [SystemMessage(content="You are a helpful voice assistant for women's career support.")]
    inserted = conversations_collection.insert_one({
        "messages": serialize_messages(new_chat),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "call_status": "in-progress"
    })
    return str(inserted.inserted_id)

@voice_bp.route("/make_call", methods=["GET"])
def make_call():
    to_phone = request.args.get('to')
    

    try:
        conversation_id = create_new_conversation()
        call = client.calls.create(
            url=url_for('voice.voice', _external=True),
            to=to_phone,
            from_="+15675571541",
            status_callback=url_for('voice.call_status', _external=True),
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            record=True
        )
        conversations_collection.update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {'call_sid': call.sid}}
        )
        return jsonify({"status": "success", "call_sid": call.sid, "conversation_id": conversation_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@voice_bp.route("/voice", methods=["POST"])
def voice():
    try:
        response = VoiceResponse()
        conversation_id = create_new_conversation()
        
        action_url = url_for('voice.handle_recording', conversation_id=conversation_id, _external=True)
        transcribe_callback = url_for('voice.handle_transcription', conversation_id=conversation_id, _external=True)
        
        response.say("Hello! Please ask your question, and I will assist you.")
        response.record(
            action=action_url,
            max_length=30,
            transcribe=True,
            transcribe_callback=transcribe_callback,
            play_beep=True
        )
        return Response(str(response), mimetype='application/xml')
    except Exception as e:
        error_response = VoiceResponse()
        error_response.say("Sorry, we're having technical difficulties. Please try again later.")
        error_response.hangup()
        return Response(str(error_response), mimetype='application/xml')

@voice_bp.route("/handle_recording", methods=["POST"])
def handle_recording():
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return Response(str(VoiceResponse().hangup()), mimetype='application/xml')

    try:
        recording_url = request.form.get('RecordingUrl')
        if recording_url:
            conversations_collection.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$set': {'recording_url': recording_url}}
            )
        return Response(str(VoiceResponse()), mimetype='application/xml')
    except Exception as e:
        return Response(str(VoiceResponse().hangup()), mimetype='application/xml')

@voice_bp.route("/handle_transcription", methods=["POST"])
def handle_transcription():
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return Response(str(VoiceResponse().say("Session error").hangup()), mimetype='application/xml')

    try:
        conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
        if not conversation:
            raise ValueError("Conversation not found")
            
        chat_history = deserialize_messages(conversation['messages'])
        transcription = request.form.get('TranscriptionText', '')
        
        response = VoiceResponse()
        
        # Process only if there's actual text
        if transcription.strip():
            # Intent detection
            intent_result = detect_intent_and_data(transcription)
            intent_type = intent_result.get("intent")
            
            if intent_type in ["signup", "update_profile"]:
                response.say(f"Let's handle your {intent_type.replace('_', ' ')} request. Please provide more details.")
            else:
                # Sentiment analysis
                sentiment = detect_sentiment(transcription)
                if sentiment == "negative":
                    empowering_msg = get_empowering_response(topic="career support")
                    response.say(empowering_msg)
                    chat_history.extend([
                        HumanMessage(content=transcription),
                        AIMessage(content=empowering_msg)
                    ])
                else:
                    # RAG response generation
                    result = rag_chain.invoke({"input": transcription, "chat_history": chat_history})
                    answer = result["answer"]
                    response.say(answer)
                    chat_history.extend([
                        HumanMessage(content=transcription),
                        AIMessage(content=answer)
                    ])
                
                # Update conversation history
                conversations_collection.update_one(
                    {'_id': ObjectId(conversation_id)},
                    {'$set': {
                        'messages': serialize_messages(chat_history),
                        'updated_at': datetime.now().isoformat()
                    }}
                )

        # Continue conversation
        response.record(
            action=url_for('voice.handle_recording', conversation_id=conversation_id, _external=True),
            max_length=30,
            transcribe=True,
            transcribe_callback=url_for('voice.handle_transcription', conversation_id=conversation_id, _external=True),
            play_beep=True
        )
        return Response(str(response), mimetype='application/xml')

    except Exception as e:
        error_response = VoiceResponse()
        error_response.say("Sorry, I encountered an error processing your request. Please try again.")
        error_response.record(
            action=url_for('voice.handle_recording', conversation_id=conversation_id, _external=True),
            max_length=30,
            transcribe=True,
            transcribe_callback=url_for('voice.handle_transcription', conversation_id=conversation_id, _external=True)
        )
        return Response(str(error_response), mimetype='application/xml')

@voice_bp.route("/call_status", methods=["POST"])
def call_status():
    try:
        status = request.form.get('CallStatus')
        call_sid = request.form.get('CallSid')
        conversations_collection.update_one(
            {'call_sid': call_sid},
            {'$set': {'call_status': status}}
        )
        return jsonify({"status": "updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500