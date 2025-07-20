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

# Firebase Admin SDK for sending messages back to app
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Firebase Admin SDK not available - Pi-to-App communication disabled")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get API key from environment variable or use default for development
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key-here')

# Get port from environment variable (Railway sets this)
PORT = int(os.environ.get('PORT', 3000))

# Initialize Firebase Admin SDK if available
firebase_app = None
if FIREBASE_AVAILABLE:
    try:
        # Use service account key from environment variable
        service_account_info = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        if service_account_info:
            cred = credentials.Certificate(json.loads(service_account_info))
            firebase_app = firebase_admin.initialize_app(cred, {
                'databaseURL': os.environ.get('FIREBASE_DATABASE_URL')
            })
            logger.info("Firebase Admin SDK initialized successfully")
        else:
            logger.warning("FIREBASE_SERVICE_ACCOUNT not set - Pi-to-App communication disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        FIREBASE_AVAILABLE = False

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

def send_status_to_app(user_id, order_id, status, message):
    """Send status update back to the app via Firebase"""
    if not FIREBASE_AVAILABLE or not firebase_app:
        logger.warning("Firebase not available - cannot send status to app")
        return False
    
    try:
        # Create status update
        status_data = {
            'orderId': order_id,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'source': 'coffee-server'
        }
        
        # Send to Firebase Realtime Database
        ref = db.reference(f'order_status/{user_id}/{order_id}')
        ref.set(status_data)
        
        logger.info(f"Status sent to app: {status} - {message}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send status to app: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'service': 'Order Notification Server',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'development'),
        'firebase_available': FIREBASE_AVAILABLE
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
        order_id = data.get('orderId', f"order_{int(time.time())}")
        orders = data.get('orders', [])
        order_count = data.get('orderCount', 0)
        total_value = data.get('totalValue', 0)
        
        # Log the order details
        logger.info(f"Order from user {user_id}: {order_count} items, total: ${total_value}")
        
        # Send "preparing" status to app
        send_status_to_app(user_id, order_id, "preparing", "Order received, starting preparation")
        
        # Trigger coffee machine (placeholder function)
        trigger_coffee_machine(orders, user_id, order_id)
        
        # Send notification (placeholder function)
        send_notification(user_id, orders, total_value)
        
        return jsonify({
            'message': 'Order notification received and processed',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'order_count': order_count,
            'total_value': total_value,
            'order_id': order_id
        })
        
    except Exception as e:
        logger.error(f"Error processing order notification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/submit-number', methods=['POST'])
def submit_number():
    """Handle order number submission from app"""
    # Rate limiting
    if is_rate_limited(request.remote_addr):
        logger.warning(f"Rate limited number submission from {request.remote_addr}")
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning(f"Invalid auth header in number submission from {request.remote_addr}")
        return jsonify({'error': 'Missing or invalid authorization header'}), 401
    
    provided_key = auth_header.split(' ')[1]
    if provided_key != API_KEY:
        logger.warning(f"Invalid API key in number submission from {request.remote_addr}")
        return jsonify({'error': 'Invalid API key'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        logger.info(f"Number submission received from {request.remote_addr}: {data}")
        
        # Extract data
        user_id = data.get('userId', 'unknown')
        order_id = data.get('orderId', 'unknown')
        number = data.get('number', 'unknown')
        
        # Log the number submission
        logger.info(f"Order number submitted by user {user_id} for order {order_id}: {number}")
        
        # Here you would typically:
        # 1. Display the number on a screen
        # 2. Print a receipt
        # 3. Update the coffee machine status
        # 4. Send confirmation back to app
        
        # For now, we'll just log it and send a confirmation
        logger.info(f"Number {number} displayed for order {order_id}")
        
        # Send confirmation status to app
        send_status_to_app(user_id, order_id, "completed", f"Order completed! Number {number} displayed.")
        
        return jsonify({
            'message': 'Order number received and displayed',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'order_id': order_id,
            'number': number,
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error processing number submission: {str(e)}")
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
        
        # Test sending a message back to app if Firebase is available
        if FIREBASE_AVAILABLE and data and 'userId' in data:
            send_status_to_app(data['userId'], 'test_order', 'test', 'Test message from Railway server')
        
        return jsonify({
            'message': 'Raspberry Pi is online and responding',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'received_data': data,
            'firebase_available': FIREBASE_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status/<user_id>/<order_id>', methods=['POST'])
def update_order_status(user_id, order_id):
    """Update order status (for manual updates or coffee machine integration)"""
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization header'}), 401
    
    provided_key = auth_header.split(' ')[1]
    if provided_key != API_KEY:
        return jsonify({'error': 'Invalid API key'}), 401
    
    try:
        data = request.get_json()
        status = data.get('status', 'unknown')
        message = data.get('message', 'Status updated')
        
        # Send status to app
        success = send_status_to_app(user_id, order_id, status, message)
        
        return jsonify({
            'success': success,
            'message': f'Status updated to: {status}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def trigger_coffee_machine(orders, user_id, order_id):
    """Trigger the coffee machine to make the ordered drinks"""
    try:
        logger.info(f"Triggering coffee machine for {len(orders)} orders")
        
        # Send "brewing" status to app
        send_status_to_app(user_id, order_id, "brewing", "Coffee machine started")
        
        # This is where you would integrate with your actual coffee machine
        # For now, we'll just log the action and simulate brewing time
        
        for i, order in enumerate(orders):
            logger.info(f"Making drink {i+1}: {order.get('name', 'Unknown drink')}")
            
            # Simulate brewing time (remove this in production)
            time.sleep(2)
            
            # Send progress update
            send_status_to_app(user_id, order_id, "brewing", f"Making drink {i+1} of {len(orders)}")
            
            # Example: You could send commands to GPIO pins here
            # import RPi.GPIO as GPIO
            # GPIO.setmode(GPIO.BCM)
            # GPIO.setup(18, GPIO.OUT)
            # GPIO.output(18, GPIO.HIGH)
            # time.sleep(5)
            # GPIO.output(18, GPIO.LOW)
        
        # Send "ready" status to app
        send_status_to_app(user_id, order_id, "ready", "Order completed and ready for pickup")
        
        logger.info("Coffee machine trigger completed")
        
    except Exception as e:
        logger.error(f"Error triggering coffee machine: {str(e)}")
        # Send error status to app
        send_status_to_app(user_id, order_id, "error", f"Error: {str(e)}")

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
    logger.info(f"Firebase Admin SDK: {'Available' if FIREBASE_AVAILABLE else 'Not available'}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=PORT, debug=False) 