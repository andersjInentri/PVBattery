from flask import Flask, jsonify, request
from datetime import datetime
from functools import wraps
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get API key from environment variable
API_KEY = os.getenv('API_KEY', 'your-secret-api-key-change-this')

def require_api_key(f):
    """Decorator to require API key for protected endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from header
        provided_key = request.headers.get('X-API-Key')

        if not provided_key:
            return jsonify({
                'error': 'API key is missing',
                'message': 'Please provide X-API-Key header'
            }), 401

        if provided_key != API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 403

        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'PVBattery API'
    }), 200

@app.route('/ping', methods=['GET'])
@require_api_key
def ping():
    """Simple ping-pong endpoint (requires API key)"""
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/echo', methods=['POST'])
@require_api_key
def echo():
    """Echo back the received JSON data (requires API key)"""
    data = request.get_json()
    return jsonify({
        'received': data,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information (public)"""
    return jsonify({
        'service': 'PVBattery API',
        'version': '1.0.0-azure',
        'endpoints': {
            'GET /': 'This information (public)',
            'GET /health': 'Health check (public)',
            'GET /ping': 'Ping-pong test (requires API key)',
            'POST /echo': 'Echo JSON data back (requires API key)'
        },
        'authentication': 'API Key required for protected endpoints',
        'header': 'X-API-Key: your-api-key'
    }), 200

if __name__ == '__main__':
    # Get port from environment variable (Azure uses PORT)
    port = int(os.environ.get('PORT', 8000))
    # Set host to 0.0.0.0 to allow external connections
    app.run(host='0.0.0.0', port=port, debug=False)
