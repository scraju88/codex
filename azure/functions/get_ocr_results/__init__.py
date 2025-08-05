import logging
import json
import os
import azure.functions as func
from azure.cosmos import CosmosClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for clients (will be initialized in main)
cosmos_client = None
database = None
screenshots_container = None
ocr_results_container = None

def initialize_clients():
    """Initialize Azure clients with error handling"""
    global cosmos_client, database, screenshots_container, ocr_results_container
    
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
        screenshots_container = database.get_container_client("screenshots")
        ocr_results_container = database.get_container_client("ocr_results")
        
        logger.info("Cosmos DB client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Cosmos DB client: {str(e)}")
        raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Get OCR results for screenshots"""
    
    # Handle CORS preflight requests
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    try:
        # Initialize clients if not already done
        if cosmos_client is None:
            initialize_clients()
        
        # Get query parameters
        screenshot_id = req.params.get('screenshot_id')
        
        if screenshot_id:
            # Get OCR results for specific screenshot
            query = f"SELECT * FROM c WHERE c.screenshot_id = '{screenshot_id}' ORDER BY c.timestamp DESC"
            items = list(ocr_results_container.query_items(query=query, enable_cross_partition_query=True))
            
            if items:
                ocr_result = items[0]  # Get the most recent result
                logger.info(f"Retrieved OCR results for screenshot: {screenshot_id}")
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'ocr_result': ocr_result
                    }),
                    status_code=200,
                    mimetype='application/json',
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    }
                )
            else:
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'OCR results not found for this screenshot'
                    }),
                    status_code=404,
                    mimetype='application/json',
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    }
                )
        else:
            # Get all OCR results with screenshot metadata
            query = "SELECT * FROM c ORDER BY c.timestamp DESC"
            ocr_items = list(ocr_results_container.query_items(query=query, enable_cross_partition_query=True))
            
            # Get screenshot metadata for each OCR result
            results_with_metadata = []
            for ocr_item in ocr_items:
                screenshot_id = ocr_item.get('screenshot_id')
                if screenshot_id:
                    # Get screenshot metadata
                    screenshot_query = f"SELECT * FROM c WHERE c.id = '{screenshot_id}'"
                    screenshot_items = list(screenshots_container.query_items(query=screenshot_query, enable_cross_partition_query=True))
                    
                    if screenshot_items:
                        screenshot_metadata = screenshot_items[0]
                        results_with_metadata.append({
                            'ocr_result': ocr_item,
                            'screenshot_metadata': {
                                'id': screenshot_metadata.get('id'),
                                'timestamp': screenshot_metadata.get('timestamp'),
                                'title': screenshot_metadata.get('title'),
                                'url': screenshot_metadata.get('url'),
                                'ocr_status': screenshot_metadata.get('ocr_status', 'unknown'),
                                'is_duplicate': screenshot_metadata.get('is_duplicate', False)
                            }
                        })
            
            logger.info(f"Retrieved {len(results_with_metadata)} OCR results")
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'ocr_results': results_with_metadata,
                    'total_count': len(results_with_metadata)
                }),
                status_code=200,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
    except Exception as e:
        logger.error(f"Error retrieving OCR results: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': f'Failed to retrieve OCR results: {str(e)}'}),
            status_code=500,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        ) 