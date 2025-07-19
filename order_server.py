#!/usr/bin/env python3
"""
Raspberry Pi Order Notification Server
Receives HTTP notifications from Firebase Cloud Functions when orders are placed
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import os
import signal
import threading
import time
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get API key from environment variable or use default for development
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key-here')

# Get port from environment variable (Railway sets this)
PORT = int(os.environ.get('PORT', 3000))

# Rate limiting
request_counts = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 10

def is_rate_limited(ip_address):
    """Check if IP is rate limited"""
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old requests
    request_counts[ip_address] = [req_time for req_time in request_counts[ip_address] 
                                 if req_time > minute_ago]
    
    # Check if too many requests
    if len(request_counts[ip_address]) >= MAX_REQUESTS_PER_MINUTE:
        return True
    
    # Add current request
    request_counts[ip_address].append(now)
    return False

def verify_firebase_ip(request):
    """Verify request comes from Firebase (optional additional security)"""
    # Firebase Cloud Functions IP ranges (you can add these)
    # This is optional but adds extra security
    firebase_ips = [
        # Add Firebase IP ranges here if needed
        # '35.199.0.0/16',
        # '35.198.0.0/16',
    ]
    
    # For now, we'll just log the IP for monitoring
    client_ip = request.remote_addr
    logger.info(f"Request from IP: {client_ip}")
    
    return True  # Allow all for now, but you can restrict to Firebase IPs

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'service': 'Order Notification Server',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'development')
    })

@app.route('/order-notification', methods=['POST'])
def order_notification():
    """Handle order notifications from Firebase"""
    # Rate limiting
    if is_rate_limited(request.remote_addr):
        logger.warning(f"Rate limited request from {request.remote_addr}")
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning(f"Invalid auth header from {request.remote_addr}")
        return jsonify({'error': 'Missing or invalid authorization header'}), 401
    
    provided_key = auth_header.split(' ')[1]
    if provided_key != API_KEY:
        logger.warning(f"Invalid API key from {request.remote_addr}")
        return jsonify({'error': 'Invalid API key'}), 401
    
    # Optional: Verify Firebase IP
    if not verify_firebase_ip(request):
        logger.warning(f"Request from non-Firebase IP: {request.remote_addr}")
        return jsonify({'error': 'Unauthorized source'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        logger.info(f"Received order notification from {request.remote_addr}: {data}")
        
        # Extract order information
        user_id = data.get('userId', 'unknown')
        orders = data.get('orders', [])
        order_count = data.get('orderCount', 0)
        total_value = data.get('totalValue', 0)
        
        # Log the order details
        logger.info(f"Order from user {user_id}: {order_count} items, total: ${total_value}")
        
        # Trigger coffee machine (placeholder function)
        trigger_coffee_machine(orders)
        
        # Send notification (placeholder function)
        send_notification(user_id, orders, total_value)
        
        return jsonify({
            'message': 'Order notification received and processed',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'order_count': order_count,
            'total_value': total_value
        })
        
    except Exception as e:
        logger.error(f"Error processing order notification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/test', methods=['POST'])
def test_endpoint():
    """Test endpoint for Firebase connection testing"""
    # Rate limiting
    if is_rate_limited(request.remote_addr):
        logger.warning(f"Rate limited test request from {request.remote_addr}")
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning(f"Invalid auth header in test from {request.remote_addr}")
        return jsonify({'error': 'Missing or invalid authorization header'}), 401
    
    provided_key = auth_header.split(' ')[1]
    if provided_key != API_KEY:
        logger.warning(f"Invalid API key in test from {request.remote_addr}")
        return jsonify({'error': 'Invalid API key'}), 401
    
    # Optional: Verify Firebase IP
    if not verify_firebase_ip(request):
        logger.warning(f"Test request from non-Firebase IP: {request.remote_addr}")
        return jsonify({'error': 'Unauthorized source'}), 403
    
    try:
        data = request.get_json()
        logger.info(f"Test request received from {request.remote_addr}: {data}")
        
        return jsonify({
            'message': 'Raspberry Pi is online and responding',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'received_data': data
        })
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def trigger_coffee_machine(orders):
    """Trigger the coffee machine to make the ordered drinks"""
    try:
        logger.info(f"Triggering coffee machine for {len(orders)} orders")
        
        # This is where you would integrate with your actual coffee machine
        # For now, we'll just log the action
        
        for i, order in enumerate(orders):
            logger.info(f"Making drink {i+1}: {order.get('name', 'Unknown drink')}")
            
            # Example: You could send commands to GPIO pins here
            # import RPi.GPIO as GPIO
            # GPIO.setmode(GPIO.BCM)
            # GPIO.setup(18, GPIO.OUT)
            # GPIO.output(18, GPIO.HIGH)
            # time.sleep(5)
            # GPIO.output(18, GPIO.LOW)
        
        logger.info("Coffee machine trigger completed")
        
    except Exception as e:
        logger.error(f"Error triggering coffee machine: {str(e)}")

def send_notification(user_id, orders, total_value):
    """Send notification about the order"""
    try:
        logger.info(f"Sending notification to user {user_id}")
        
        # This is where you would integrate with notification services
        # Examples: Email, SMS, Push notifications, etc.
        
        # For now, we'll just log the notification
        notification_text = f"Order received: {len(orders)} items, total: ${total_value}"
        logger.info(f"Notification: {notification_text}")
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")

if __name__ == '__main__':
    logger.info(f"Starting Order Notification Server on port {PORT}")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'your-secure-api-key-here' else 'No'}")
    logger.info(f"Rate limiting: {MAX_REQUESTS_PER_MINUTE} requests per minute per IP")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=PORT, debug=False) 