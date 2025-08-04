// EMR Assistant Background Script
class BackgroundManager {
    constructor() {
        this.state = {
            isCapturing: false,
            captureInterval: 1500, // Default interval
            screenshotCount: 0,
            serverUrl: 'https://emr-assistant-functions.azurewebsites.net/api', // Azure Functions
            serverConnected: false, // Start disconnected
            lastCaptureTime: null,
            captureTimer: null,
            uploadQueue: [], // Queue for failed uploads
            settings: {
                quality: 0.8,
                maxRetries: 3,
                enableNotifications: true
            }
        };
        
        this.init();
    }
    
    async init() {
        await this.loadState();
        this.setupMessageHandlers();
        this.checkServerConnection();
    }
    
    async loadState() {
        try {
            const result = await chrome.storage.local.get([
                'isCapturing',
                'captureInterval',
                'screenshotCount',
                'serverUrl',
                'settings'
            ]);
            
            this.state = { ...this.state, ...result };
        } catch (error) {
            console.error('Error loading state:', error);
        }
    }
    
    async saveState() {
        try {
            await chrome.storage.local.set({
                isCapturing: this.state.isCapturing,
                captureInterval: this.state.captureInterval,
                screenshotCount: this.state.screenshotCount,
                serverUrl: this.state.serverUrl,
                settings: this.state.settings
            });
        } catch (error) {
            console.error('Error saving state:', error);
        }
    }
    
    setupMessageHandlers() {
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // Keep message channel open for async response
        });
    }
    
    async handleMessage(message, sender, sendResponse) {
        try {
            switch (message.action) {
                case 'getState':
                    sendResponse({
                        success: true,
                        data: {
                            isCapturing: this.state.isCapturing,
                            screenshotCount: this.state.screenshotCount,
                            serverStatus: this.state.serverConnected ? 'connected' : 'disconnected',
                            lastUpdate: this.state.lastCaptureTime
                        }
                    });
                    break;
                    
                case 'startCapture':
                    await this.startCapture();
                    sendResponse({ success: true });
                    break;
                    
                case 'stopCapture':
                    await this.stopCapture();
                    sendResponse({ success: true });
                    break;
                    
                case 'updateSettings':
                    await this.updateSettings(message.settings);
                    sendResponse({ success: true });
                    break;
                    
                case 'getSettings':
                    sendResponse({
                        success: true,
                        data: this.state.settings
                    });
                    break;
                    
                case 'getScreenshotStats':
                    sendResponse({
                        success: true,
                        data: {
                            totalScreenshots: this.state.screenshotCount,
                            screenshotsInMemory: this.state.screenshots ? this.state.screenshots.length : 0,
                            uploadQueueSize: this.state.uploadQueue.length,
                            lastCaptureTime: this.state.lastCaptureTime,
                            isCapturing: this.state.isCapturing,
                            serverConnected: this.state.serverConnected
                        }
                    });
                    break;
                    
                default:
                    sendResponse({
                        success: false,
                        error: 'Unknown action'
                    });
            }
        } catch (error) {
            console.error('Error handling message:', error);
            sendResponse({
                success: false,
                error: error.message
            });
        }
    }
    
    async startCapture() {
        if (this.state.isCapturing) {
            console.log('Capture already in progress');
            return;
        }
        
        try {
        this.state.isCapturing = true;
        await this.saveState();
        
        // Start capture timer
        this.state.captureTimer = setInterval(() => {
            this.captureScreenshot();
        }, this.state.captureInterval);
        
        // Notify popup
        this.notifyPopup({
            action: 'statusUpdate',
            data: { isCapturing: true }
        });
        
            console.log('Capture started successfully');
        } catch (error) {
            console.error('Error starting capture:', error);
            this.state.isCapturing = false;
            throw error;
        }
    }
    
    async stopCapture() {
        if (!this.state.isCapturing) {
            console.log('Capture not in progress');
            return;
        }
        
        try {
        this.state.isCapturing = false;
        await this.saveState();
        
        // Stop capture timer
        if (this.state.captureTimer) {
            clearInterval(this.state.captureTimer);
            this.state.captureTimer = null;
        }
        
        // Notify popup
        this.notifyPopup({
            action: 'statusUpdate',
            data: { isCapturing: false }
        });
        
            console.log('Capture stopped successfully');
        } catch (error) {
            console.error('Error stopping capture:', error);
            this.state.isCapturing = true;
            throw error;
        }
    }
    
    async captureScreenshot() {
        try {
            // Get current active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            if (!tab) {
                console.warn('No active tab found');
                return;
            }
            
            // Check if tab is accessible
            if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
                console.warn('Cannot capture chrome:// or extension pages');
                return;
            }
            
            // Capture screenshot with quality settings
            const captureOptions = {
                format: 'png',
                quality: Math.floor(this.state.settings.quality * 100)
            };
            
            console.log('Capturing screenshot with options:', captureOptions);
            const dataUrl = await chrome.tabs.captureVisibleTab(null, captureOptions);
            
            if (!dataUrl) {
                throw new Error('Screenshot capture returned null');
            }
            
            // Process screenshot
            await this.processScreenshot(dataUrl, tab);
            
            this.state.lastCaptureTime = Date.now();
            this.state.screenshotCount++;
            await this.saveState();
            
            // Notify popup
            this.notifyPopup({
                action: 'captureComplete',
                data: { 
                    timestamp: this.state.lastCaptureTime,
                    screenshotCount: this.state.screenshotCount,
                    tabUrl: tab.url,
                    tabTitle: tab.title
                }
            });
            
            console.log('Screenshot captured successfully:', {
                timestamp: this.state.lastCaptureTime,
                count: this.state.screenshotCount,
                size: dataUrl.length,
                url: tab.url
            });
            
        } catch (error) {
            console.error('Error capturing screenshot:', error);
            this.notifyPopup({
                action: 'error',
                message: `Failed to capture screenshot: ${error.message}`
            });
        }
    }
    
    async processScreenshot(dataUrl, tab) {
        // Process screenshot data
        const screenshotData = {
            id: this.generateScreenshotId(),
            timestamp: Date.now(),
            url: tab.url,
            title: tab.title,
            dataUrl: dataUrl,
            size: dataUrl.length,
            quality: this.state.settings.quality
        };
        
        console.log('Processing screenshot:', {
            id: screenshotData.id,
            url: screenshotData.url,
            size: screenshotData.size,
            quality: screenshotData.quality
        });
        
        // Upload to server
        await this.uploadScreenshot(screenshotData);
        
        // Store screenshot data temporarily as backup
        if (!this.state.screenshots) {
            this.state.screenshots = [];
        }
        
        // Keep only the last 10 screenshots in memory as backup
        if (this.state.screenshots.length >= 10) {
            this.state.screenshots.shift(); // Remove oldest
        }
        
        this.state.screenshots.push(screenshotData);
        
        // Log processing completion
        console.log(`Screenshot processed and uploaded. Total in memory: ${this.state.screenshots.length}`);
    }
    
    generateScreenshotId() {
        return `screenshot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    async uploadScreenshot(screenshotData) {
        try {
            // Check if server is connected
            if (!this.state.serverConnected) {
                console.log('Server not connected, adding to upload queue');
                this.state.uploadQueue.push(screenshotData);
                return;
            }
            
            // Prepare upload data
            const uploadData = {
                screenshot: screenshotData.dataUrl,
                metadata: {
                    id: screenshotData.id,
                    url: screenshotData.url,
                    title: screenshotData.title,
                    timestamp: screenshotData.timestamp,
                    quality: screenshotData.quality,
                    size: screenshotData.size
                }
            };
            
            console.log('Uploading screenshot to server:', {
                id: screenshotData.id,
                url: this.state.serverUrl.replace('/api', '') + '/api/upload-screenshot'
            });
            
            // Upload to server
            const response = await fetch(`${this.state.serverUrl.replace('/api', '')}/api/upload-screenshot`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(uploadData)
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Screenshot uploaded successfully:', result);
            
            // Update server status
            this.state.serverConnected = true;
            this.notifyPopup({
                action: 'statusUpdate',
                data: { serverStatus: 'connected' }
            });
            
        } catch (error) {
            console.error('Upload failed:', error);
            
            // Add to retry queue
            this.state.uploadQueue.push({
                ...screenshotData,
                retryCount: 0,
                lastRetry: Date.now()
            });
            
            // Update server status
            this.state.serverConnected = false;
            this.notifyPopup({
                action: 'statusUpdate',
                data: { serverStatus: 'disconnected' }
            });
            
            // Schedule retry
            this.scheduleRetry();
        }
    }
    
    async scheduleRetry() {
        // Process upload queue with exponential backoff
        if (this.state.uploadQueue.length > 0) {
            const now = Date.now();
            const retryableItems = this.state.uploadQueue.filter(item => {
                const timeSinceLastRetry = now - (item.lastRetry || 0);
                const backoffDelay = Math.pow(2, item.retryCount || 0) * 1000; // 1s, 2s, 4s, 8s
                return timeSinceLastRetry >= backoffDelay;
            });
            
            for (const item of retryableItems) {
                if (item.retryCount >= this.state.settings.maxRetries) {
                    console.log('Max retries reached for screenshot:', item.id);
                    // Remove from queue
                    this.state.uploadQueue = this.state.uploadQueue.filter(q => q.id !== item.id);
                    continue;
                }
                
                // Retry upload
                item.retryCount = (item.retryCount || 0) + 1;
                item.lastRetry = now;
                
                console.log(`Retrying upload for screenshot ${item.id} (attempt ${item.retryCount})`);
                await this.uploadScreenshot(item);
            }
        }
        
        // Schedule next retry check
        setTimeout(() => {
            this.scheduleRetry();
        }, 5000); // Check every 5 seconds
    }
    
    async updateSettings(newSettings) {
        this.state.settings = { ...this.state.settings, ...newSettings };
        await this.saveState();
        
        // Update capture interval if changed
        if (newSettings.captureInterval && this.state.isCapturing) {
            await this.stopCapture();
            this.state.captureInterval = newSettings.captureInterval;
            await this.startCapture();
        }
    }
    
    async checkServerConnection() {
        try {
            console.log('Checking server connection:', this.state.serverUrl + '/health');
            
            const response = await fetch(`${this.state.serverUrl.replace('/api', '')}/api/health`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            this.state.serverConnected = response.ok;
            console.log('Server connection status:', this.state.serverConnected ? 'connected' : 'disconnected');
            
            // If server is now connected, try to upload queued items
            if (this.state.serverConnected && this.state.uploadQueue.length > 0) {
                console.log('Server reconnected, processing upload queue...');
                this.processUploadQueue();
            }
            
        } catch (error) {
            console.error('Server connection check failed:', error);
            this.state.serverConnected = false;
        }
        
        // Notify popup of server status
        this.notifyPopup({
            action: 'statusUpdate',
            data: {
                serverStatus: this.state.serverConnected ? 'connected' : 'disconnected'
            }
        });
        
        // Check again in 30 seconds
        setTimeout(() => {
            this.checkServerConnection();
        }, 30000);
    }
    
    async processUploadQueue() {
        if (this.state.uploadQueue.length === 0) return;
        
        console.log(`Processing upload queue with ${this.state.uploadQueue.length} items`);
        
        // Process queue items
        const itemsToProcess = [...this.state.uploadQueue];
        this.state.uploadQueue = []; // Clear queue
        
        for (const item of itemsToProcess) {
            try {
                await this.uploadScreenshot(item);
            } catch (error) {
                console.error('Failed to upload queued item:', error);
                // Re-add to queue for retry
                this.state.uploadQueue.push(item);
            }
        }
    }
    
    notifyPopup(message) {
        chrome.runtime.sendMessage(message).catch(error => {
            // Popup might not be open, ignore errors
            console.log('Popup notification failed:', error.message);
        });
    }
    
    // Handle extension installation/update
    handleInstalled(details) {
        if (details.reason === 'install') {
            console.log('EMR Assistant installed');
            // Set default settings
            this.saveState();
        } else if (details.reason === 'update') {
            console.log('EMR Assistant updated');
            // Handle any migration if needed
        }
    }
}

// Initialize background manager
const backgroundManager = new BackgroundManager();

// Handle extension installation/update
chrome.runtime.onInstalled.addListener((details) => {
    backgroundManager.handleInstalled(details);
});

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('EMR Assistant started');
}); 