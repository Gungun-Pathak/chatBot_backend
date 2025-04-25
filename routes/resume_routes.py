from flask import Blueprint, request, jsonify
from service.resume_service import extract_text_from_resume, analyze_resume

resume_bp = Blueprint('resume', __name__)

@resume_bp.route('/analyze_resume', methods=['POST'])
def analyze_resume_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No resume file uploaded'}), 400

    file = request.files['file']
    try:
        resume_text = extract_text_from_resume(file)
        analysis = analyze_resume(resume_text)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
