import logging
import json
import os
import base64
from datetime import datetime
from typing import List, Dict, Any
import azure.functions as func
from azure.cosmos import CosmosClient
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Global variables for clients (will be initialized in main)
cosmos_client = None
database = None
container = None

CHANGE_DETECTION_THRESHOLD = 8

def initialize_clients():
    """Initialize Azure clients with error handling"""
    global cosmos_client, database, container
    
    try:
        # Get environment variables
        cosmos_endpoint = os.environ.get('COSMOS_ENDPOINT')
        cosmos_key = os.environ.get('COSMOS_KEY')
        
        # Validate environment variables
        if not cosmos_endpoint:
            raise ValueError("COSMOS_ENDPOINT environment variable is not set")
        if not cosmos_key:
            raise ValueError("COSMOS_KEY environment variable is not set")
        
        # Initialize Cosmos DB client
        cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
        database = cosmos_client.get_database_client("emr-assistant")
        container = database.get_container_client("screenshots")
        
        logger.info("Cosmos DB client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Cosmos DB client: {str(e)}")
        raise

def calculate_perceptual_hash(screenshot_data: str) -> str:
    """Calculate perceptual hash of an image using multi-scale analysis"""
    try:
        # Remove data URL prefix
        if screenshot_data.startswith('data:image/'):
            screenshot_data = screenshot_data.split(',')[1]
        
        # Decode base64 image
        img_data = base64.b64decode(screenshot_data)
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to grayscale
        img_gray = img.convert('L')
        
        # Multi-scale analysis: compare at different resolutions
        scales = [32, 64, 128]  # Different resolution levels
        hashes = []
        
        for scale in scales:
            # Resize image to current scale
            img_resized = img_gray.resize((scale, scale))
            img_array = np.array(img_resized)
            
            # Calculate mean and standard deviation for this scale
            mean_value = np.mean(img_array)
            std_value = np.std(img_array)
            
            # Create hash using both mean and std thresholds
            hash_bits = []
            for pixel in img_array.flatten():
                if pixel > mean_value + std_value * 0.5:
                    hash_bits.append('1')
                elif pixel < mean_value - std_value * 0.5:
                    hash_bits.append('0')
                else:
                    hash_bits.append('2')  # Middle range
            
            hashes.append(''.join(hash_bits))
        
        # Combine hashes from all scales
        combined_hash = '|'.join(hashes)
        
        logger.info(f"Generated multi-scale hash: {combined_hash[:50]}... (length: {len(combined_hash)})")
        
        return combined_hash
        
    except Exception as e:
        logger.error(f"Error calculating perceptual hash: {str(e)}")
        return ""

def calculate_hash_difference(hash1: str, hash2: str) -> float:
    """Calculate the weighted difference between two multi-scale hashes"""
    if not hash1 or not hash2:
        return float('inf')
    
    try:
        # Split hashes by scale (separated by '|')
        scales1 = hash1.split('|')
        scales2 = hash2.split('|')
        
        if len(scales1) != len(scales2):
            return float('inf')
        
        total_difference = 0
        weights = [1.0, 0.7, 0.5]  # Weight different scales differently
        
        for i, (scale1, scale2) in enumerate(zip(scales1, scales2)):
            if len(scale1) != len(scale2):
                continue
            
            # Calculate difference for this scale
            scale_diff = 0
            for a, b in zip(scale1, scale2):
                if a != b:
                    # Weight differences based on the values
                    if a == '2' or b == '2':  # Middle range changes
                        scale_diff += 0.5
                    else:  # Binary changes
                        scale_diff += 1.0
            
            # Apply weight for this scale
            total_difference += scale_diff * weights[i]
        
        return total_difference
        
    except Exception as e:
        logger.error(f"Error calculating hash difference: {str(e)}")
        return float('inf')

def get_recent_screenshots_from_db() -> List[Dict]:
    """Get recent screenshots from Cosmos DB for change detection"""
    try:
        # Query recent screenshots ordered by timestamp
        query = "SELECT c.perceptual_hash, c.id, c.blob_name FROM c ORDER BY c.timestamp DESC OFFSET 0 LIMIT 5"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        return items
    except Exception as e:
        logger.error(f"Error querying recent screenshots: {str(e)}")
        return []

def detect_significant_change(current_hash: str, previous_hashes: List[str]) -> bool:
    """Detect if current screenshot has significant changes using multi-scale analysis"""
    if not previous_hashes:
        logger.info("No previous hashes found - first screenshot")
        return True  # First screenshot always has "change"
    
    logger.info(f"Comparing current hash with {len(previous_hashes)} previous hashes")
    
    # Use a lower threshold for more sensitive detection
    threshold = CHANGE_DETECTION_THRESHOLD * 0.5
    
    # Compare with last few screenshots
    for i, prev_hash in enumerate(previous_hashes[-3:]):  # Check last 3 screenshots
        if not prev_hash:  # Skip empty hashes
            continue
            
        difference = calculate_hash_difference(current_hash, prev_hash)
        logger.info(f"Multi-scale difference to previous hash {i}: {difference:.2f} (threshold: {threshold:.2f})")
        
        # If current screenshot is similar to ANY of the last 3, it's a duplicate
        if difference <= threshold:
            logger.info(f"Duplicate detected - difference {difference:.2f} <= threshold {threshold:.2f}")
            return False  # No significant change (it's a duplicate)
    
    logger.info("Significant change detected - different from all previous screenshots")
    return True  # Significant change (not a duplicate)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Change detection endpoint"""
    
    # Handle CORS preflight requests
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    try:
        # Initialize clients if not already done
        if cosmos_client is None:
            initialize_clients()
        
        # Parse request
        data = req.get_json()
        
        if not data or 'screenshot' not in data:
            return func.HttpResponse(
                json.dumps({'error': 'Missing screenshot data'}),
                status_code=400,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        screenshot_data = data['screenshot']
        
        # Validate screenshot data
        if not screenshot_data.startswith('data:image/'):
            return func.HttpResponse(
                json.dumps({'error': 'Invalid screenshot format'}),
                status_code=400,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        # Calculate perceptual hash
        current_hash = calculate_perceptual_hash(screenshot_data)
        
        if not current_hash:
            logger.warning("Failed to calculate perceptual hash - assuming change")
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'has_significant_change': True,
                    'current_hash': None,
                    'previous_hashes_count': 0,
                    'message': 'Hash calculation failed - assuming change'
                }),
                status_code=200,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        # Get recent screenshots from Cosmos DB for change detection
        recent_screenshots = get_recent_screenshots_from_db()
        previous_hashes = [s.get('perceptual_hash', '') for s in recent_screenshots]
        
        # Detect significant change
        has_significant_change = detect_significant_change(current_hash, previous_hashes)
        
        logger.info(f"Change detection result: {has_significant_change}")
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'has_significant_change': has_significant_change,
                'current_hash': current_hash,
                'previous_hashes_count': len(previous_hashes),
                'message': 'Change detection completed'
            }),
            status_code=200,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in change detection: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': f'Change detection failed: {str(e)}'}),
            status_code=500,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        ) 