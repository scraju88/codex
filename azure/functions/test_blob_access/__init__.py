import logging
import os
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Test blob storage access"""
    
    try:
        # Get environment variables
        connection_string = os.environ.get('STORAGE_CONNECTION_STRING')
        
        if not connection_string:
            return func.HttpResponse(
                json.dumps({'error': 'STORAGE_CONNECTION_STRING not found'}),
                status_code=500,
                mimetype='application/json'
            )
        
        # Initialize Blob Storage client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client("screenshots")
        
        # List blobs
        blobs = list(container_client.list_blobs())
        blob_names = [blob.name for blob in blobs]
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'blob_count': len(blob_names),
                'blob_names': blob_names[:10],  # First 10 blobs
                'connection_string_found': True
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
        logger.error(f"Error testing blob access: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'error': f'Failed to access blob storage: {str(e)}',
                'connection_string_found': 'STORAGE_CONNECTION_STRING' in os.environ
            }),
            status_code=500,
            mimetype='application/json',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        ) 