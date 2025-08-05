import logging
import os
import json
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from datetime import datetime
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for clients (will be initialized in main)
blob_service_client = None
cosmos_client = None
database = None
screenshots_container = None
ocr_results_container = None

def initialize_clients():
    """Initialize Azure clients with error handling"""
    global blob_service_client, cosmos_client, database, screenshots_container, ocr_results_container
    
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
        
        # Initialize Blob Storage client
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        
        # Initialize Cosmos DB client
        cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
        database = cosmos_client.get_database_client("emr-assistant")
        screenshots_container = database.get_container_client("screenshots")
        ocr_results_container = database.get_container_client("ocr_results")
        
        logger.info("Azure clients initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Azure clients: {str(e)}")
        raise

def call_azure_vision_api(image_bytes: bytes) -> dict:
    """Call Azure Computer Vision API for OCR"""
    try:
        # Get Azure Computer Vision credentials
        vision_endpoint = os.environ.get('VISION_ENDPOINT')
        vision_key = os.environ.get('VISION_KEY')
        
        if not vision_endpoint or not vision_key:
            raise ValueError("VISION_ENDPOINT or VISION_KEY not set")
        
        # Prepare the API call
        headers = {
            'Ocp-Apim-Subscription-Key': vision_key,
            'Content-Type': 'application/octet-stream'
        }
        
        # Call the Read API (async operation)
        read_url = f"{vision_endpoint}/vision/v3.2/read/analyze"
        
        logger.info("Calling Azure Computer Vision API...")
        response = requests.post(read_url, headers=headers, data=image_bytes)
        
        if response.status_code == 202:  # Accepted
            # Get the operation location
            operation_location = response.headers.get('Operation-Location')
            
            # Poll for completion
            max_retries = 10
            for i in range(max_retries):
                time.sleep(1)  # Wait 1 second between polls
                
                poll_response = requests.get(operation_location, headers={'Ocp-Apim-Subscription-Key': vision_key})
                
                if poll_response.status_code == 200:
                    result = poll_response.json()
                    
                    if result.get('status') == 'succeeded':
                        logger.info("OCR processing completed successfully")
                        return result
                    elif result.get('status') == 'failed':
                        raise Exception(f"OCR processing failed: {result}")
                    # If still running, continue polling
                else:
                    raise Exception(f"Failed to poll OCR status: {poll_response.status_code}")
            
            raise Exception("OCR processing timed out")
        else:
            raise Exception(f"Failed to start OCR processing: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Error calling Azure Computer Vision API: {str(e)}")
        raise

def extract_text_from_ocr_result(ocr_result: dict) -> dict:
    """Extract and format text from OCR result"""
    try:
        text_blocks = []
        full_text = ""
        word_count = 0
        
        # Extract text from read results
        if 'analyzeResult' in ocr_result and 'readResults' in ocr_result['analyzeResult']:
            for page in ocr_result['analyzeResult']['readResults']:
                for line in page.get('lines', []):
                    line_text = line.get('text', '')
                    bounding_box = line.get('boundingBox', [])
                    
                    text_blocks.append({
                        'text': line_text,
                        'confidence': 0.95,  # Azure doesn't provide per-line confidence
                        'bounding_box': bounding_box,
                        'type': 'line'
                    })
                    
                    full_text += line_text + "\n"
                    word_count += len(line_text.split())
        
        return {
            'text_blocks': text_blocks,
            'full_text': full_text.strip(),
            'word_count': word_count,
            'processing_time_ms': int(time.time() * 1000)  # Approximate
        }
        
    except Exception as e:
        logger.error(f"Error extracting text from OCR result: {str(e)}")
        raise

def update_screenshot_ocr_status(screenshot_id: str, status: str, ocr_results_id: str = None):
    """Update screenshot metadata with OCR status"""
    try:
        # Get the screenshot document
        query = f"SELECT * FROM c WHERE c.id = '{screenshot_id}'"
        items = list(screenshots_container.query_items(query=query, enable_cross_partition_query=True))
        
        if items:
            screenshot_doc = items[0]
            screenshot_doc['ocr_status'] = status
            if ocr_results_id:
                screenshot_doc['ocr_results_id'] = ocr_results_id
            
            screenshots_container.upsert_item(screenshot_doc)
            logger.info(f"Updated screenshot {screenshot_id} OCR status to {status}")
        
    except Exception as e:
        logger.error(f"Error updating screenshot OCR status: {str(e)}")

def cleanup_old_ocr_results():
    """Cleanup old OCR results to maintain FIFO (50 limit)"""
    try:
        # Query OCR results ordered by timestamp
        query = "SELECT * FROM c ORDER BY c.timestamp DESC"
        items = list(ocr_results_container.query_items(query=query, enable_cross_partition_query=True))
        
        # Keep only the latest 50 OCR results
        max_ocr_results = 50
        if len(items) > max_ocr_results:
            items_to_delete = items[max_ocr_results:]
            
            for item in items_to_delete:
                ocr_results_container.delete_item(item, partition_key=item['id'])
                logger.info(f"Deleted old OCR result: {item['id']}")
                
    except Exception as e:
        logger.error(f"Error cleaning up old OCR results: {str(e)}")

def main(req: func.HttpRequest) -> func.HttpResponse:
    """OCR processor endpoint"""
    
    # Handle CORS preflight requests
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    try:
        # Initialize clients if not already done
        if blob_service_client is None:
            initialize_clients()
        
        # Parse request
        data = req.get_json()
        
        if not data or 'screenshot_id' not in data or 'blob_name' not in data:
            return func.HttpResponse(
                json.dumps({'error': 'Invalid request data - missing screenshot_id or blob_name'}),
                status_code=400,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        screenshot_id = data['screenshot_id']
        blob_name = data['blob_name']
        
        logger.info(f"Starting OCR processing for screenshot: {screenshot_id}")
        
        # Update screenshot status to processing
        update_screenshot_ocr_status(screenshot_id, 'processing')
        
        # Download image from blob storage
        blob_client = blob_service_client.get_container_client("screenshots").get_blob_client(blob_name)
        image_bytes = blob_client.download_blob().readall()
        
        logger.info(f"Downloaded image: {len(image_bytes)} bytes")
        
        # Call Azure Computer Vision API
        ocr_result = call_azure_vision_api(image_bytes)
        
        # Extract text from OCR result
        text_data = extract_text_from_ocr_result(ocr_result)
        
        # Create OCR results document
        ocr_results_id = f"ocr_{screenshot_id}"
        ocr_doc = {
            'id': ocr_results_id,
            'screenshot_id': screenshot_id,
            'timestamp': datetime.now().isoformat(),
            'text_blocks': text_data['text_blocks'],
            'full_text': text_data['full_text'],
            'word_count': text_data['word_count'],
            'processing_time_ms': text_data['processing_time_ms']
        }
        
        # Store OCR results in Cosmos DB
        ocr_results_container.upsert_item(ocr_doc)
        
        # Update screenshot status to completed
        update_screenshot_ocr_status(screenshot_id, 'completed', ocr_results_id)
        
        # Cleanup old OCR results
        cleanup_old_ocr_results()
        
        logger.info(f"OCR processing completed for screenshot: {screenshot_id}")
        logger.info(f"Extracted {text_data['word_count']} words")
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'screenshot_id': screenshot_id,
                'ocr_results_id': ocr_results_id,
                'word_count': text_data['word_count'],
                'message': 'OCR processing completed successfully'
            }),
            status_code=200,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in OCR processing: {str(e)}")
        
        # Update screenshot status to failed if we have the ID
        if 'screenshot_id' in locals():
            update_screenshot_ocr_status(screenshot_id, 'failed')
        
        return func.HttpResponse(
            json.dumps({'error': f'OCR processing failed: {str(e)}'}),
            status_code=500,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        ) 