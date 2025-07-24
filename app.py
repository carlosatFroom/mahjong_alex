#!/usr/bin/env python3
"""
Flask API for Mahjong Tutor
Provides endpoints for chat functionality with content filtering
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from content_filter import ContentFilter


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables
content_filter = None
groq_client = None

def init_services():
    """Initialize AI services"""
    global content_filter, groq_client
    
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    content_filter = ContentFilter(groq_api_key)
    groq_client = Groq(api_key=groq_api_key)
    
    logger.info("Services initialized successfully")

def get_client_ip():
    """Get client IP address from request"""
    # Check for forwarded headers first (common with proxies/load balancers)
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers['X-Real-IP']
    else:
        return request.remote_addr

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'mahjong-tutor'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        message = data.get('message', '').strip()
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get client IP
        client_ip = get_client_ip()
        
        # Handle image data if provided
        image_data = data.get('image')
        
        # Filter content
        allowed, filter_result = content_filter.filter_content(message, client_ip, image_data)
        
        if not allowed:
            logger.warning(f"Content blocked from {client_ip}: {filter_result.reason}")
            return jsonify({
                'error': 'Content not allowed',
                'reason': filter_result.reason,
                'filter_stage': filter_result.filter_stage
            }), 403
        
        # Generate response
        response = generate_mahjong_response(message, image_data)
        
        # Log successful interaction
        logger.info(f"Successful chat from {client_ip}, tokens: {filter_result.tokens_used}")
        
        return jsonify({
            'response': response,
            'timestamp': datetime.utcnow().isoformat(),
            'tokens_used': filter_result.tokens_used
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def generate_mahjong_response(message: str, image_data: str = None) -> str:
    """Generate response using Groq API"""
    
    # System prompt for Mahjong tutor
#     system_prompt = """You are a helpful Mahjong tutor and strategy advisor. You specialize in:

# 1. Mahjong tile strategy and optimal play
# 2. Hand analysis and tile discarding decisions
# 3. Scoring rules and game mechanics
# 4. Tournament strategies and advanced techniques

# Key guidelines:
# - Focus exclusively on Mahjong-related topics
# - Provide clear, actionable advice
# - Explain your reasoning for strategy recommendations
# - Be encouraging and educational
# - If shown an image of tiles, analyze the position and suggest optimal moves
# - If shown a card, analyze the card and suggest optimal moves
# Remember: You should only discuss Mahjong gameplay, rules, and strategy."""
    with open('year2025.txt', 'r') as file:
        card_info = file.read()
    system_prompt = f"""You are an expert Mahjong tutor specializing in American Mahjong using the 2025 National Mah Jongg League (NMJL) card. Your role is to help players improve their skills by providing strategic guidance, hand analysis, and constructive feedback.

Your expertise includes:

    1. Hand Categories Knowledge: You have memorized all categories from the 2025 NMJL card:
        2025 hands
        2468 (evens)
        Any Like Numbers
        Quints
        Consecutive Runs
        13579 (odds)
        Winds and Dragons
        369
        Singles and Pairs

    2. Strategic Guidance: You can:
        Analyze tiles to identify potential winning hands
        Recommend which hand(s) to pursue based on current tiles
        Explain when to switch between hands
        Advise on defensive play to prevent opponents from winning
        Guide Charleston strategy and tile passing decisions
        Teach proper calling (exposure) timing

    3. Hand Values: You understand the point values (X=exposed, C=concealed) and can explain risk/reward tradeoffs between pursuing higher-value hands versus more achievable lower-value hands.

    4. Teaching Approach:
        Break down complex hands into understandable components
        Use clear notation (F=Flower, D=Dragon, N/E/W/S=Winds)
        Provide examples using actual tile combinations
        Explain why certain decisions are optimal
        Identify common mistakes and how to avoid them

    5. Adaptive Feedback: Tailor advice to the player's skill level, from beginner (focusing on basic hand recognition) to advanced (discussing probability, defensive strategies, and reading opponents).

When analyzing hands or providing feedback, always reference specific hands from the 2025 card, explain the requirements clearly, and help players understand both offensive and defensive considerations. Use encouraging language while providing constructive criticism.
And the 2025 card information is as follows:
{card_info}"""
    # Load environment variables
    load_dotenv()

    # Get API key from environment variables
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    # Add image if provided
    if image_data:
        messages[1] = {
            "role": "user", 
            "content": [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        }
    
    # Generate response
    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=messages,
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].message.content

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        stats = content_filter.get_system_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'Unable to retrieve stats'}), 500

@app.route('/api/ip-stats/<ip>', methods=['GET'])
def get_ip_stats(ip):
    """Get statistics for a specific IP"""
    try:
        stats = content_filter.get_ip_stats(ip)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"IP stats error: {str(e)}")
        return jsonify({'error': 'Unable to retrieve IP stats'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        init_services()
        host = os.getenv('SERVER_HOST', '0.0.0.0')
        port = int(os.getenv('SERVER_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        
        logger.info(f"Starting Mahjong Tutor API on port {port}")
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise