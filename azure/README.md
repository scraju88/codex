# EMR Assistant - Azure Deployment

This guide will help you deploy the EMR Assistant to Azure, replacing the local server with Azure Functions and cloud storage.

## 🏗️ Architecture

### **Azure Services Used:**
- **Azure Functions**: Serverless API endpoints
- **Azure Blob Storage**: Screenshot storage
- **Azure Cosmos DB**: Metadata storage
- **Azure App Service**: Function hosting

### **Data Flow:**
```
Chrome Extension → Azure Functions → Blob Storage + Cosmos DB
```

## 🚀 Quick Deployment

### **Prerequisites:**
1. **Azure CLI** installed and logged in
2. **PowerShell** (for Windows) or **Bash** (for Mac/Linux)
3. **Azure subscription** with billing enabled

### **Step 1: Deploy Azure Resources**
```powershell
# Navigate to azure directory
cd codex/azure

# Run deployment script
./deploy.ps1
```

### **Step 2: Update Configuration**
After deployment, update the configuration files with your Azure resource details:

#### **Update `config.json`:**
```json
{
  "storage": {
    "accountName": "emrassistantstorage",
    "containerName": "screenshots",
    "connectionString": "YOUR_STORAGE_CONNECTION_STRING"
  },
  "functionApp": {
    "name": "emr-assistant-functions",
    "url": "https://emr-assistant-functions.azurewebsites.net",
    "apiKey": "YOUR_FUNCTION_APP_KEY"
  }
}
```

#### **Update `local.settings.json`:**
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "YOUR_STORAGE_CONNECTION_STRING",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "STORAGE_CONNECTION_STRING": "YOUR_STORAGE_CONNECTION_STRING",
    "COSMOS_ENDPOINT": "YOUR_COSMOS_ENDPOINT",
    "COSMOS_KEY": "YOUR_COSMOS_KEY"
  }
}
```

### **Step 3: Deploy Functions**
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Navigate to functions directory
cd codex/azure/functions

# Deploy functions
func azure functionapp publish emr-assistant-functions
```

### **Step 4: Update Chrome Extension**
The extension has been updated to use Azure Functions. The server URL is now:
```
https://emr-assistant-functions.azurewebsites.net/api
```

## 📊 Azure Resources Created

### **Resource Group:**
- **Name**: `emr-assistant-rg`
- **Location**: `eastus`

### **Storage Account:**
- **Name**: `emrassistantstorage`
- **Container**: `screenshots`
- **Purpose**: Store screenshot images

### **Cosmos DB:**
- **Account**: `emr-assistant-cosmos`
- **Database**: `emr-assistant`
- **Container**: `screenshots`
- **Purpose**: Store screenshot metadata

### **Function App:**
- **Name**: `emr-assistant-functions`
- **Runtime**: Python 3.9
- **Plan**: Consumption (serverless)
- **Purpose**: API endpoints

## 🔧 API Endpoints

### **Health Check:**
```
GET https://emr-assistant-functions.azurewebsites.net/api/health
```

### **Upload Screenshot:**
```
POST https://emr-assistant-functions.azurewebsites.net/api/upload-screenshot
```

### **Get Screenshots:**
```
GET https://emr-assistant-functions.azurewebsites.net/api/screenshots
```

## 💰 Cost Estimation

### **Azure Functions (Consumption Plan):**
- **Free tier**: 1M requests/month
- **Additional**: $0.20 per million requests

### **Blob Storage:**
- **Free tier**: 5GB/month
- **Additional**: $0.0184 per GB/month

### **Cosmos DB:**
- **Free tier**: 1000 RU/s and 25GB storage
- **Additional**: $0.008 per 100 RU/s/hour

### **Estimated Monthly Cost:**
- **Low usage** (< 1000 screenshots): ~$5-10/month
- **Medium usage** (1000-10000 screenshots): ~$15-25/month
- **High usage** (> 10000 screenshots): ~$30-50/month

## 🔒 Security & Compliance

### **Authentication:**
- **Function App**: Anonymous access (can be secured with Azure AD)
- **Storage**: Connection string authentication
- **Cosmos DB**: Key-based authentication

### **Data Protection:**
- **Encryption at rest**: Enabled by default
- **Encryption in transit**: TLS 1.2+
- **Backup**: Automatic backups for Cosmos DB

### **HIPAA Compliance:**
- **Azure Functions**: HIPAA eligible
- **Blob Storage**: HIPAA eligible
- **Cosmos DB**: HIPAA eligible

## 🛠️ Development & Testing

### **Local Development:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run functions locally
cd codex/azure/functions
func start
```

### **Testing:**
```bash
# Test health endpoint
curl https://emr-assistant-functions.azurewebsites.net/api/health

# Test screenshot upload
curl -X POST https://emr-assistant-functions.azurewebsites.net/api/upload-screenshot \
  -H "Content-Type: application/json" \
  -d '{"screenshot": "data:image/png;base64,...", "metadata": {...}}'
```

## 🔍 Monitoring & Logging

### **Azure Application Insights:**
- **Function monitoring**: Automatic
- **Performance metrics**: Response times, throughput
- **Error tracking**: Exception monitoring

### **Logs:**
- **Function logs**: Available in Azure portal
- **Storage logs**: Enabled via Azure Storage Analytics
- **Cosmos DB logs**: Available via Azure Monitor

## 🚨 Troubleshooting

### **Common Issues:**

#### **1. Function App Not Responding:**
- Check if functions are deployed correctly
- Verify connection strings in app settings
- Check function app logs in Azure portal

#### **2. Storage Connection Issues:**
- Verify storage account name and connection string
- Check if blob container exists
- Ensure proper permissions

#### **3. Cosmos DB Connection Issues:**
- Verify endpoint and key
- Check if database and container exist
- Ensure proper partition key configuration

### **Debug Commands:**
```bash
# Check function app status
az functionapp show --name emr-assistant-functions --resource-group emr-assistant-rg

# View function logs
az functionapp logs tail --name emr-assistant-functions --resource-group emr-assistant-rg

# Test function locally
func start --verbose
```

## 📈 Scaling

### **Automatic Scaling:**
- **Functions**: Scale automatically based on demand
- **Storage**: No scaling limits
- **Cosmos DB**: Can be configured for auto-scaling

### **Manual Scaling:**
```bash
# Scale function app
az functionapp plan update --name emr-assistant-functions --resource-group emr-assistant-rg --sku B1

# Scale Cosmos DB
az cosmosdb sql container update --account-name emr-assistant-cosmos --resource-group emr-assistant-rg --database-name emr-assistant --name screenshots --throughput 1000
```

## 🗑️ Cleanup

### **Remove All Resources:**
```bash
# Delete resource group (removes all resources)
az group delete --name emr-assistant-rg --yes
```

### **Remove Individual Resources:**
```bash
# Delete function app
az functionapp delete --name emr-assistant-functions --resource-group emr-assistant-rg

# Delete storage account
az storage account delete --name emrassistantstorage --resource-group emr-assistant-rg

# Delete Cosmos DB
az cosmosdb delete --name emr-assistant-cosmos --resource-group emr-assistant-rg
```

## 📞 Support

For issues or questions:
1. Check Azure portal logs
2. Review function app monitoring
3. Test endpoints individually
4. Verify configuration settings

---

**🎯 The EMR Assistant is now ready for Azure deployment!** 