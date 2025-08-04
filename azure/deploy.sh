#!/bin/bash

# Azure Deployment Script for EMR Assistant (Bash Version)
# Run this script to set up all Azure resources in US West 2

# Default values
RESOURCE_GROUP_NAME="emr-assistant-rg"
LOCATION="westus2"
STORAGE_ACCOUNT_NAME="emrassistantstorage"
FUNCTION_APP_NAME="emr-assistant-functions"

echo "🚀 Starting Azure deployment for EMR Assistant..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

# 1. Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP_NAME --location $LOCATION

# 2. Create Storage Account
echo "💾 Creating storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2

# 3. Create Blob Container
echo "📁 Creating blob container..."
az storage container create \
    --name screenshots \
    --account-name $STORAGE_ACCOUNT_NAME

# 4. Get Storage Connection String
echo "🔑 Getting storage connection string..."
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --query connectionString \
    --output tsv)

# 5. Create Cosmos DB Account
echo "🗄️ Creating Cosmos DB account..."
az cosmosdb create \
    --name "emr-assistant-cosmos" \
    --resource-group $RESOURCE_GROUP_NAME \
    --locations regionName=$LOCATION

# 6. Create Cosmos DB Database
echo "📊 Creating Cosmos DB database..."
az cosmosdb sql database create \
    --account-name "emr-assistant-cosmos" \
    --resource-group $RESOURCE_GROUP_NAME \
    --name "emr-assistant"

# 7. Create Cosmos DB Container
echo "📦 Creating Cosmos DB container..."
az cosmosdb sql container create \
    --account-name "emr-assistant-cosmos" \
    --resource-group $RESOURCE_GROUP_NAME \
    --database-name "emr-assistant" \
    --name "screenshots" \
    --partition-key-path "/id"

# 8. Get Cosmos DB Keys
echo "🔑 Getting Cosmos DB keys..."
COSMOS_ENDPOINT=$(az cosmosdb show \
    --name "emr-assistant-cosmos" \
    --resource-group $RESOURCE_GROUP_NAME \
    --query documentEndpoint \
    --output tsv)

COSMOS_KEY=$(az cosmosdb keys list \
    --name "emr-assistant-cosmos" \
    --resource-group $RESOURCE_GROUP_NAME \
    --query primaryMasterKey \
    --output tsv)

# 9. Create Function App
echo "⚡ Creating function app..."
az functionapp create \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --functions-version 4 \
    --storage-account $STORAGE_ACCOUNT_NAME \
    --os-type Linux

# 10. Configure Function App Settings
echo "⚙️ Configuring function app settings..."
az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --settings \
    "STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING" \
    "COSMOS_ENDPOINT=$COSMOS_ENDPOINT" \
    "COSMOS_KEY=$COSMOS_KEY"

echo "✅ Azure deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "   Resource Group: $RESOURCE_GROUP_NAME"
echo "   Storage Account: $STORAGE_ACCOUNT_NAME"
echo "   Function App: $FUNCTION_APP_NAME"
echo "   Cosmos DB: emr-assistant-cosmos"
echo ""
echo "🌐 Function App URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
echo ""
echo "🔑 Connection Strings:"
echo "   Storage: $STORAGE_CONNECTION_STRING"
echo "   Cosmos Endpoint: $COSMOS_ENDPOINT"
echo "   Cosmos Key: $COSMOS_KEY"
echo ""
echo "📝 Next steps:"
echo "   1. Update config files with the connection strings above"
echo "   2. Deploy functions: cd azure/functions && func azure functionapp publish $FUNCTION_APP_NAME"
echo "   3. Test endpoints: curl https://$FUNCTION_APP_NAME.azurewebsites.net/api/health" 