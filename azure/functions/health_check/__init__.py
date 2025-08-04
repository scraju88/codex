import azure.functions as func
import logging
import json
from datetime import datetime
from azure.cosmos import CosmosClient
import os

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
    """Health check endpoint"""
    try:
        # Initialize clients if not already done
        if cosmos_client is None:
            initialize_clients()
        
        # Count screenshots in Cosmos DB
        query = "SELECT VALUE COUNT(1) FROM c"
        result = list(container.query_items(query=query, enable_cross_partition_query=True))
        screenshot_count = result[0] if result else 0
        
        return func.HttpResponse(
            json.dumps({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'screenshots_stored': screenshot_count,
                'max_screenshots': 50
            }),
            status_code=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }),
            status_code=500,
            mimetype='application/json'
        ) 