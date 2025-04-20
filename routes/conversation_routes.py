from flask import Blueprint, jsonify
from flask_cors import CORS
from bson import ObjectId
from config import conversations_collection

conversation_bp = Blueprint('conversation', __name__)
CORS(conversation_bp)


@conversation_bp.route('/conversations', methods=['GET'])
def get_conversations():
    conversations = list(conversations_collection.find({}, {'messages': 0}).sort('updated_at', -1).limit(20))
    for conv in conversations:
        conv['_id'] = str(conv['_id'])
    return jsonify(conversations)

@conversation_bp.route('/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    try:
        conversation = conversations_collection.find_one({'_id': ObjectId(conversation_id)})
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        conversation['_id'] = str(conversation['_id'])
        return jsonify(conversation)
    except:
        return jsonify({'error': 'Invalid conversation ID'}), 400

@conversation_bp.route('/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    try:
        result = conversations_collection.delete_one({'_id': ObjectId(conversation_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Conversation not found'}), 404
        return jsonify({'status': 'success'})
    except:
        return jsonify({'error': 'Invalid conversation ID'}), 400
