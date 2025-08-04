#!/usr/bin/env python3
"""
EMR Assistant Server
Clean, structured server using modular architecture
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
from app.services.screenshot_service import ScreenshotService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for extension

# Initialize services
screenshot_service = ScreenshotService(max_screenshots=50, change_detection_threshold=8)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    stats = screenshot_service.get_stats()
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'screenshots_stored': stats['screenshots_stored'],
        'max_screenshots': stats['max_screenshots']
    })

@app.route('/api/upload-screenshot', methods=['POST'])
def upload_screenshot():
    """Upload screenshot endpoint with change detection"""
    try:
        data = request.get_json()
        
        if not data or 'screenshot' not in data or 'metadata' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        screenshot_data = data['screenshot']
        metadata = data['metadata']
        
        # Validate screenshot data
        if not screenshot_data.startswith('data:image/'):
            return jsonify({'error': 'Invalid screenshot format'}), 400
        
        # Use screenshot service to handle the upload
        result = screenshot_service.add_screenshot(screenshot_data, metadata)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error uploading screenshot: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/screenshots', methods=['GET'])
def get_screenshots():
    """Get list of stored screenshots"""
    screenshots = screenshot_service.get_screenshots()
    stats = screenshot_service.get_stats()
    return jsonify({
        'screenshots': screenshots,
        'total': stats['screenshots_stored'],
        'max': stats['max_screenshots']
    })

@app.route('/api/clear-screenshots', methods=['POST'])
def clear_screenshots():
    """Clear all stored screenshots"""
    result = screenshot_service.clear_screenshots()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    stats = screenshot_service.get_stats()
    stats['server_time'] = datetime.now().isoformat()
    return jsonify(stats)

@app.route('/api/change-detection', methods=['GET', 'POST'])
def change_detection_settings():
    """Get or update change detection settings"""
    if request.method == 'GET':
        stats = screenshot_service.get_stats()
        return jsonify({
            'enabled': stats['change_detection_enabled'],
            'threshold': stats['change_detection_threshold']
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        enabled = data.get('enabled') if data else None
        threshold = data.get('threshold') if data else None
        
        result = screenshot_service.update_change_detection_settings(enabled, threshold)
        return jsonify({
            'success': True,
            **result
        })

if __name__ == '__main__':
    logger.info("Starting EMR Assistant server...")
    logger.info("Server will be available at: http://localhost:5100")
    logger.info("Health check: http://localhost:5100/api/health")
    logger.info("Screenshots: http://localhost:5100/api/screenshots")
    logger.info("Stats: http://localhost:5100/api/stats")
    
    app.run(host='0.0.0.0', port=5100, debug=True) 