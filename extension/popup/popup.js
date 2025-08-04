// EMR Assistant Popup JavaScript
class PopupManager {
    constructor() {
        this.elements = {};
        this.state = {
            isCapturing: false,
            screenshotCount: 0,
            serverStatus: 'connected',
            lastUpdate: null
        };
        
        this.init();
    }
    
    init() {
        this.getElements();
        this.bindEvents();
        this.loadState();
        this.updateUI();
    }
    
    getElements() {
        this.elements = {
            captureBtn: document.getElementById('captureBtn'),
            statusText: document.getElementById('statusText'),
            progressBar: document.getElementById('progressBar'),
            screenshotCount: document.getElementById('screenshotCount'),
            memoryCount: document.getElementById('memoryCount'),
            uploadQueueSize: document.getElementById('uploadQueueSize'),
            serverStatus: document.getElementById('serverStatus'),
            lastCaptureItem: document.getElementById('lastCaptureItem'),
            lastCaptureTime: document.getElementById('lastCaptureTime'),
            settingsBtn: document.getElementById('settingsBtn'),
            helpBtn: document.getElementById('helpBtn')
        };
    }
    
    bindEvents() {
        // Capture button
        this.elements.captureBtn.addEventListener('click', () => {
            this.toggleCapture();
        });
        
        // Settings button
        this.elements.settingsBtn.addEventListener('click', () => {
            this.openSettings();
        });
        
        // Help button
        this.elements.helpBtn.addEventListener('click', () => {
            this.showHelp();
        });
        
        // Listen for messages from background script
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message);
        });
    }
    
    async loadState() {
        try {
            // Get current state from background script
            const response = await this.sendMessage({ action: 'getState' });
            if (response.success) {
                this.state = { ...this.state, ...response.data };
            }
            
            // Get screenshot statistics
            const statsResponse = await this.sendMessage({ action: 'getScreenshotStats' });
            if (statsResponse.success) {
                this.state = { ...this.state, ...statsResponse.data };
            }
            
            this.updateUI();
        } catch (error) {
            console.error('Error loading state:', error);
            this.showError('Failed to load extension state');
        }
    }
    
    async toggleCapture() {
        try {
            const action = this.state.isCapturing ? 'stopCapture' : 'startCapture';
            const response = await this.sendMessage({ action });
            
            if (response.success) {
                // Don't update local state immediately - wait for background confirmation
                // The background script will send a statusUpdate message
                this.showStatus(this.state.isCapturing ? 'Stopping capture...' : 'Starting capture...');
            } else {
                this.showError(response.error || 'Failed to toggle capture');
            }
        } catch (error) {
            console.error('Error toggling capture:', error);
            this.showError('Failed to toggle capture');
        }
    }
    
    openSettings() {
        chrome.runtime.openOptionsPage();
    }
    
    showHelp() {
        // Open help page or show help modal
        chrome.tabs.create({
            url: 'https://your-help-page.com'
        });
    }
    
    handleMessage(message) {
        switch (message.action) {
            case 'statusUpdate':
                this.state = { ...this.state, ...message.data };
                this.updateUI();
                
                // Show confirmation message for capture state changes
                if (message.data.hasOwnProperty('isCapturing')) {
                    this.showStatus(message.data.isCapturing ? 'Capture started' : 'Capture stopped');
                }
                break;
                
            case 'error':
                this.showError(message.message);
                break;
                
            case 'captureComplete':
                // Update screenshot count from background
                if (message.data.screenshotCount) {
                    this.state.screenshotCount = message.data.screenshotCount;
                } else {
                    this.state.screenshotCount = (this.state.screenshotCount || 0) + 1;
                }
                
                // Store last capture info
                this.state.lastCapture = {
                    timestamp: message.data.timestamp,
                    url: message.data.tabUrl,
                    title: message.data.tabTitle
                };
                
                this.updateUI();
                this.showStatus(`Screenshot captured from: ${message.data.tabTitle || 'Unknown page'}`);
                break;
                
            default:
                console.log('Unknown message:', message);
        }
    }
    
    updateUI() {
        // Update capture button
        if (this.state.isCapturing) {
            this.elements.captureBtn.textContent = '🛑 Stop Capture';
            this.elements.captureBtn.classList.add('capturing');
        } else {
            this.elements.captureBtn.textContent = '📸 Start Capture';
            this.elements.captureBtn.classList.remove('capturing');
        }
        
        // Update status text
        if (this.state.isCapturing) {
            this.elements.statusText.textContent = 'Capturing screenshots...';
            this.elements.statusText.classList.add('loading');
        } else {
            this.elements.statusText.textContent = 'Ready to capture';
            this.elements.statusText.classList.remove('loading');
        }
        
        // Update screenshot count
        this.elements.screenshotCount.textContent = this.state.screenshotCount || 0;
        
        // Update memory count
        this.elements.memoryCount.textContent = this.state.screenshotsInMemory || 0;
        
        // Update upload queue size
        this.elements.uploadQueueSize.textContent = this.state.uploadQueueSize || 0;
        
        // Update server status
        this.elements.serverStatus.textContent = this.state.serverStatus || 'Connected';
        this.elements.serverStatus.className = `stat-value ${this.state.serverStatus}`;
        
        // Update last capture time
        if (this.state.lastCaptureTime) {
            const lastCapture = new Date(this.state.lastCaptureTime);
            const timeAgo = this.getTimeAgo(lastCapture);
            this.elements.lastCaptureTime.textContent = timeAgo;
            this.elements.lastCaptureItem.style.display = 'flex';
        } else {
            this.elements.lastCaptureItem.style.display = 'none';
        }
        
        // Update status container
        const statusContainer = document.querySelector('.status');
        statusContainer.classList.remove('error', 'success');
        
        if (this.state.serverStatus === 'disconnected' || this.state.serverStatus === 'error') {
            statusContainer.classList.add('error');
        } else if (this.state.isCapturing) {
            statusContainer.classList.add('success');
        }
    }
    
    showStatus(message) {
        this.elements.statusText.textContent = message;
        setTimeout(() => {
            if (!this.state.isCapturing) {
                this.elements.statusText.textContent = 'Ready to capture';
            }
        }, 3000);
    }
    
    showError(message) {
        this.elements.statusText.textContent = `Error: ${message}`;
        const statusContainer = document.querySelector('.status');
        statusContainer.classList.add('error');
        
        setTimeout(() => {
            statusContainer.classList.remove('error');
            this.updateUI();
        }, 5000);
    }
    
    async sendMessage(message) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(message, (response) => {
                if (chrome.runtime.lastError) {
                    reject(new Error(chrome.runtime.lastError.message));
                } else {
                    resolve(response);
                }
            });
        });
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return `${diffInSeconds}s ago`;
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes}m ago`;
        } else {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours}h ago`;
        }
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PopupManager();
}); 