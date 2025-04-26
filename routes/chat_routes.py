from flask import Blueprint, request, jsonify
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime
import json
import logging

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

import re

import json
import re
import logging

def structure_rag_response(answer):
    """Process RAG response into structured format with fallback handling"""
    structured_fallback = {
        "summary": answer,
        "sections": [],
        "links": [],
        "actions": []
    }

    try:
        # First try direct JSON parsing
        try:
            parsed = json.loads(answer)
            if validate_structure(parsed):
                return parsed
        except json.JSONDecodeError:
            pass  # Proceed to pattern matching

        # Pattern match for JSON in text
        json_match = re.search(r'\{[\s\S]*\}', answer)
        if json_match:
            clean_json = json_match.group()
            parsed = json.loads(clean_json)
            if validate_structure(parsed):
                return parsed

        # If no valid JSON found, create structure from text
        return create_structured_fallback(answer)

    except Exception as e:
        logging.error(f"Structured parsing failed: {str(e)}")
        return create_structured_fallback(answer)

def validate_structure(data):
    """Validate the structure has at least one valid section"""
    required_keys = {"summary", "sections", "links", "actions"}
    return (
        isinstance(data, dict) and 
        required_keys.issubset(data.keys()) and 
        isinstance(data.get("sections"), list)
    )

def create_structured_fallback(text):
    """Create structured data from plain text"""
    title = "Key Information"
    is_job = False

    # detect type
    if "Job" in text or "Company" in text or "requirements" in text.lower():
        title = "Job Details"
        is_job = True
    elif "Dates" in text or "Location" in text:
        title = "Event Details"

    return {
        "summary": text,
        "sections": [{
            "title": title,
            "content": extract_key_details(text),
            "icon": "info"
        }],
        "links": extract_links(text, is_job=is_job),
        "actions": []
    }



def detect_job_context(text):
    """Detect if the text seems job-related"""
    job_keywords = ["Position", "Company", "Location", "Posted", "Focus", "Apply", "Career"]
    return any(keyword.lower() in text.lower() for keyword in job_keywords)

def extract_key_details(text):
    """Extract key details using enhanced pattern matching"""
    event_patterns = {
        "Dates?": r"(Dates?:?)\s*(.+?)(?=\n|$)",
        "Location": r"(Location:?)\s*(.+?)(?=\n|$)",
        "Type": r"(Type:?)\s*(.+?)(?=\n|$)",
        "Focus": r"(Focus:?)\s*(.+?)(?=\n|$)"
    }
    
    job_patterns = {
        "Company": r"(Company:?)\s*(.+?)(?=\n|$)",
        "Location": r"(Location:?)\s*(.+?)(?=\n|$)",
        "Requirements": r"(Requirements?:?)\s*(.+?)(?=\n|$)",
        "Benefits": r"(Benefits?:?)\s*(.+?)(?=\n|$)",
    }
    
    details = []
    
    # First try event patterns
    for label, pattern in event_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            details.append(f"{match[0]} {match[1]}".strip())
    
    if not details:
        # Try job patterns if event fields not found
        for label, pattern in job_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                details.append(f"{match[0]} {match[1]}".strip())
    
    return details if details else [text]

def extract_links(text, is_job):
    """Extract URLs with context"""
    url_pattern = r'(https?://\S+)'
    
    if is_job:
        link_text_pattern = r'(\b(?:Apply|Careers?|Career Page)\b:?\s*)(https?://\S+)'
    else:
        link_text_pattern = r'(\b(?:Website|Register|Details)\b:?\s*)(https?://\S+)'

    links = []

    # Try to find links with context first
    for match in re.finditer(link_text_pattern, text, re.IGNORECASE):
        links.append({
            "text": match.group(1).replace(":", "").strip(),
            "url": match.group(2),
            "type": "career" if is_job else "website"
        })

    # Fallback: if no labeled links found, find bare URLs
    if not links:
        urls = re.findall(url_pattern, text)
        links = [{
            "text": "Company Careers Page" if is_job else "More Information",
            "url": url,
            "type": "career" if is_job else "website"
        } for url in urls]

    return links

def extract_actions(text, is_job):
    """Extract action links"""
    actions = []

    if is_job:
        action_pattern = r'(Apply Now):?\s*(https?://\S+)'
        for match in re.finditer(action_pattern, text, re.IGNORECASE):
            actions.append({
                "type": "apply",
                "text": match.group(1).strip(),
                "url": match.group(2)
            })
    else:
        action_pattern = r'(Register Now):?\s*(https?://\S+)'
        for match in re.finditer(action_pattern, text, re.IGNORECASE):
            actions.append({
                "type": "register",
                "text": match.group(1).strip(),
                "url": match.group(2)
            })

    return actions

def generate_fallback_text(structured_data):
    """Convert structured response to readable text format"""
    if not structured_data or not isinstance(structured_data, dict):
        return "Here's the information I found:"

    text_parts = []

    # Add summary
    if structured_data.get('summary'):
        text_parts.append(f"📌 {structured_data['summary']}")

    # Process sections
    for section in structured_data.get('sections', []):
        section_text = []
        if section.get('title'):
            section_text.append(f"\n**{section['title']}**")
        for item in section.get('content', []):
            section_text.append(f"• {item.strip('**')}")  # Remove markdown bold
        text_parts.append("\n".join(section_text))

    # Process links
    if structured_data.get('links'):
        text_parts.append("\n🔗 Useful Links:")
        for link in structured_data['links']:
            text_parts.append(f"- {link.get('text', 'Link')}: {link.get('url', '')}")

    # Process actions
    if structured_data.get('actions'):
        text_parts.append("\n📝 Actions:")
        for action in structured_data['actions']:
            text_parts.append(f"- {action.get('text', 'Action available')}")

    return "\n".join(text_parts) if text_parts else "Please see the structured response."
@chat_bp.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question")
    conversation_id = data.get("conversation_id")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        # Intent detection
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

        # Conversation history management
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

        # Sentiment analysis and empowerment
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

        # Bias detection
        nlp_result = nlp_based_bias_detector(question)
        gemini_result = gemini_bias_detector(question)

        # RAG processing
        result = rag_chain.invoke({"input": question, "chat_history": chat_history})
        answer = result["answer"]
        
        # Structure the response
        structured_response = structure_rag_response(answer)
        fallback_text = generate_fallback_text(structured_response)
        
        # Update conversation history with both formats
        chat_history += [
            HumanMessage(content=question),
            AIMessage(content=json.dumps({
                "text": fallback_text,
                "structured": structured_response
            }))
        ]
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
            "response": fallback_text,
            "structured_response": structured_response,
            "conversation_id": conversation_id,
            "messages": updated,
            "intent": "general",
            "sentiment": sentiment
        })

    except Exception as e:
        logging.error(f"Chat error: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Unable to process request",
            "details": str(e)
        }), 500