from flask import Blueprint, request, jsonify
from config import users_collection, conversations_collection
from bson import ObjectId
from datetime import datetime
import re
from flask_cors import CORS
import logging

user_bp = Blueprint("user", __name__)
CORS(user_bp, origins=["http://localhost:5173"], methods=["POST"], allow_headers=["Content-Type"])

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@user_bp.route("/sign_up", methods=["POST"])
def sign_up():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        email = data.get("email", "").strip()
        if not email or not is_valid_email(email):
            return jsonify({"error": "Valid email is required"}), 400

        # Required fields validation
        required_fields = ["name", "email"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check existing users
        phone = data.get("phone", "").strip()
        if phone and users_collection.find_one({"phone": phone}):
            return jsonify({"error": "Phone number already in use"}), 409

        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({
                "message": "User already exists",
                "user_id": str(existing_user["_id"]),
                "user": format_user(existing_user)
            }), 200

        # Create new user
        new_user = {
            "name": data["name"].strip(),
            "email": email,
            "phone": phone,
            "skills": data.get("skills", []),
            "bio": data.get("bio", "").strip(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Database insertion
        user_result = users_collection.insert_one(new_user)
        new_user_data = users_collection.find_one({"_id": user_result.inserted_id})

        return jsonify({
            "message": "User signed up successfully",
            "user_id": str(new_user_data["_id"]),
            "user": format_user(new_user_data)
        }), 201

    except Exception as e:
        logging.error(f"Signup error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route("/update_profile", methods=["POST"])
def update_profile():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        email = data.get("email", "").strip()
        if not email or not is_valid_email(email):
            return jsonify({"error": "Valid email is required to update profile"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "User not found"}), 404

        update_fields = {}
        allowed_fields = ["name", "phone", "skills", "bio"]
        for field in allowed_fields:
            if field in data:
                value = data[field]
                update_fields[field] = value.strip() if isinstance(value, str) else value

        if not update_fields:
            return jsonify({"error": "No fields provided for update"}), 400

        update_fields["updated_at"] = datetime.utcnow().isoformat()
        users_collection.update_one({"_id": user["_id"]}, {"$set": update_fields})
        updated_user = users_collection.find_one({"_id": user["_id"]})

        return jsonify({
            "message": "Profile updated successfully",
            "user_id": str(updated_user["_id"]),
            "updated_fields": update_fields,
            "user": format_user(updated_user)
        }), 200

    except Exception as e:
        logging.error(f"Update profile error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def format_user(user):
    return {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "skills": user.get("skills", []),
        "bio": user.get("bio", ""),
        "created_at": user.get("created_at", ""),
        "updated_at": user.get("updated_at", "")
    }