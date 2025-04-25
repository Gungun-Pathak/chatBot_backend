from flask import Flask
from flask_cors import CORS
from routes.chat_routes import chat_bp
from routes.conversation_routes import conversation_bp
from routes.user_routes import user_bp 
from routes.voice_routes import voice_bp
from routes.resume_routes import resume_bp

app = Flask(__name__)
CORS(app, 
     origins=["http://localhost:5173", "https://chat-bot-frontend-topaz.vercel.app"],
     methods=["GET", "POST", "PUT", "DELETE"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

@app.route("/", methods=["GET"])
def home():
    return {"message": "🟢 Backend is live!"}, 200



# Register Blueprints
def register_routes(app):
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(conversation_bp, url_prefix="/conversation")
    app.register_blueprint(user_bp, url_prefix="/user") 
    app.register_blueprint(voice_bp, url_prefix='/voice')
    app.register_blueprint(resume_bp, url_prefix="/resume")

register_routes(app)

if __name__ == "__main__":
    print("🚀 Starting Flask server...")
    app.run(debug=True)
