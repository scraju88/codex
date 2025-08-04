import logging
import os
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for clients (will be initialized in main)
blob_service_client = None
container_client = None

def initialize_clients():
    """Initialize Azure clients with error handling"""
    global blob_service_client, container_client
    
    try:
        # Get environment variables
        connection_string = os.environ.get('STORAGE_CONNECTION_STRING')
        
        # Validate environment variables
        if not connection_string:
            raise ValueError("STORAGE_CONNECTION_STRING environment variable is not set")
        
        logger.info("Connection string found, initializing blob client...")
        
        # Initialize Blob Storage client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("screenshots")
        
        logger.info("Blob Storage client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Blob Storage client: {str(e)}")
        raise

def main(req: func.HttpRequest, blob_name: str) -> func.HttpResponse:
    """Get screenshot image from blob storage"""
    
    logger.info(f"Received request for blob: {blob_name}")
    
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
        if blob_service_client is None:
            logger.info("Initializing clients...")
            initialize_clients()
        
        logger.info(f"Getting blob client for: {blob_name}")
        
        # Get blob client for the specified blob name
        blob_client = container_client.get_blob_client(blob_name)
        
        # Check if blob exists
        if not blob_client.exists():
            logger.error(f"Blob does not exist: {blob_name}")
            return func.HttpResponse(
                json.dumps({'error': f'Blob not found: {blob_name}'}),
                status_code=404,
                mimetype='application/json',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        logger.info(f"Downloading blob: {blob_name}")
        
        # Download the blob content
        blob_data = blob_client.download_blob()
        image_bytes = blob_data.readall()
        
        logger.info(f"Successfully retrieved image: {blob_name}, size: {len(image_bytes)} bytes")
        
        # Return the image with appropriate headers
        return func.HttpResponse(
            body=image_bytes,
            status_code=200,
            mimetype='image/png',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Cache-Control': 'public, max-age=3600'  # Cache for 1 hour
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving image {blob_name}: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': f'Failed to retrieve image: {str(e)}'}),
            status_code=500,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        ) 