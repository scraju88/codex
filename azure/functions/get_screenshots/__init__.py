import logging
import json
import os
from datetime import datetime
import azure.functions as func
from azure.cosmos import CosmosClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for clients (will be initialized in main)
cosmos_client = None
database = None
container = None

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

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Get list of stored and skipped screenshots"""
    
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
        
        # Query all screenshots from Cosmos DB
        query = "SELECT * FROM c ORDER BY c.timestamp DESC"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        # Calculate statistics
        total_stored = len([item for item in items if not item.get('is_duplicate', False)])
        total_duplicates = len([item for item in items if item.get('is_duplicate', False)])
        total = len(items)
        
        logger.info(f"Retrieved {total} screenshots: {total_stored} stored, {total_duplicates} duplicates")
        
        return func.HttpResponse(
            json.dumps({
                'screenshots': items,
                'total_stored': total_stored,
                'total_duplicates': total_duplicates,
                'total': total
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
        logger.error(f"Error retrieving screenshots: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': f'Failed to retrieve screenshots: {str(e)}'}),
            status_code=500,
            mimetype='application/json'
        ) 