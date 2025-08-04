import logging
import json
import os
import base64
from datetime import datetime
from typing import List, Dict, Any
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for clients (will be initialized in main)
blob_service_client = None
container_client = None
cosmos_client = None
database = None
container = None

MAX_SCREENSHOTS = 50

def initialize_clients():
    """Initialize Azure clients with error handling"""
    global blob_service_client, container_client, cosmos_client, database, container
    
    try:
        # Get environment variables
        storage_connection_string = os.environ.get('STORAGE_CONNECTION_STRING')
        cosmos_endpoint = os.environ.get('COSMOS_ENDPOINT')
        cosmos_key = os.environ.get('COSMOS_KEY')
        
        # Validate environment variables
        if not storage_connection_string:
            raise ValueError("STORAGE_CONNECTION_STRING environment variable is not set")
        if not cosmos_endpoint:
            raise ValueError("COSMOS_ENDPOINT environment variable is not set")
        if not cosmos_key:
            raise ValueError("COSMOS_KEY environment variable is not set")
        
        # Initialize Azure clients
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        container_client = blob_service_client.get_container_client("screenshots")
        
        cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
        database = cosmos_client.get_database_client("emr-assistant")
        container = database.get_container_client("screenshots")
        
        logger.info("Azure clients initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Azure clients: {str(e)}")
        raise



def cleanup_old_screenshots():
    """Remove old screenshots to maintain FIFO limit"""
    try:
        # Get total count
        count_query = "SELECT VALUE COUNT(1) FROM c"
        count_result = list(container.query_items(query=count_query, enable_cross_partition_query=True))
        total_count = count_result[0] if count_result else 0
        
        if total_count > MAX_SCREENSHOTS:
            # Get oldest screenshots to delete
            delete_query = "SELECT c.id, c.blob_name FROM c ORDER BY c.timestamp ASC OFFSET 0 LIMIT 1"
            old_items = list(container.query_items(query=delete_query, enable_cross_partition_query=True))
            
            for old_item in old_items:
                old_id = old_item['id']
                old_blob_name = old_item.get('blob_name')
                
                # Delete from Cosmos DB
                container.delete_item(item=old_id, partition_key=old_id)
                logger.info(f"Deleted old metadata: {old_id}")
                
                # Delete from Blob Storage
                if old_blob_name:
                    old_blob_client = container_client.get_blob_client(old_blob_name)
                    old_blob_client.delete_blob()
                    logger.info(f"Deleted old blob: {old_blob_name}")
                    
    except Exception as e:
        logger.error(f"Error cleaning up old screenshots: {str(e)}")

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Upload screenshot endpoint"""
    
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
        if blob_service_client is None:
            initialize_clients()
        
        # Parse request
        data = req.get_json()
        
        if not data or 'screenshot' not in data or 'metadata' not in data:
            return func.HttpResponse(
                json.dumps({'error': 'Invalid request data'}),
                status_code=400,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        screenshot_data = data['screenshot']
        metadata = data['metadata']
        
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
        
        # Call change detection function
        try:
            import requests
            
            # Get the function app URL from environment or construct it
            function_app_name = os.environ.get('WEBSITE_SITE_NAME', 'emr-assistant-functions')
            change_detection_url = f"https://{function_app_name}.azurewebsites.net/api/change-detection"
            
            # Prepare the request
            payload = {
                'screenshot': screenshot_data
            }
            
            # Call the change detection function
            response = requests.post(
                change_detection_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                change_result = response.json()
                has_significant_change = change_result.get('has_significant_change', True)
                current_hash = change_result.get('current_hash')
                logger.info(f"Change detection result: {has_significant_change}")
            else:
                logger.error(f"Change detection failed: {response.status_code} - {response.text}")
                has_significant_change = True  # Fallback: assume change detected
                current_hash = None
                
        except Exception as e:
            logger.error(f"Error calling change detection: {str(e)}")
            has_significant_change = True  # Fallback: assume change detected
            current_hash = None
        
        # Generate screenshot ID (always store, but mark duplicates)
        screenshot_id = f"screenshot_{datetime.now().timestamp()}_{metadata.get('id', 'unknown')}"
        
        # Extract base64 data for blob storage
        if screenshot_data.startswith('data:image/'):
            base64_data = screenshot_data.split(',')[1]
        else:
            base64_data = screenshot_data
        
        # Convert base64 to bytes
        image_bytes = base64.b64decode(base64_data)
        
        # Upload to Blob Storage (always store)
        blob_name = f"{screenshot_id}.png"
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(image_bytes, overwrite=True)
        
        # Store metadata in Cosmos DB with duplicate flag
        screenshot_doc = {
            'id': screenshot_id,
            'timestamp': datetime.now().isoformat(),
            'url': metadata.get('url', ''),
            'title': metadata.get('title', ''),
            'quality': metadata.get('quality', 0.8),
            'size': len(image_bytes),
            'blob_name': blob_name,
            'perceptual_hash': current_hash,
            'has_significant_change': has_significant_change,
            'is_duplicate': not has_significant_change  # Mark as duplicate if no significant change
        }
        
        container.upsert_item(screenshot_doc)
        
        # Cleanup old screenshots to maintain FIFO
        cleanup_old_screenshots()
        
        logger.info(f"Screenshot uploaded successfully: {screenshot_id}")
        logger.info(f"Has significant change: {has_significant_change}")
        logger.info(f"Is duplicate: {not has_significant_change}")
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'id': screenshot_id,
                'has_significant_change': has_significant_change,
                'is_duplicate': not has_significant_change,
                'message': f'Screenshot uploaded successfully ({"duplicate" if not has_significant_change else "new"})'
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
        logger.error(f"Error uploading screenshot: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': f'Upload failed: {str(e)}'}),
            status_code=500,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        ) 