// EMR Assistant Content Script
// This script is injected into web pages and can interact with the page DOM

class ContentScriptManager {
    constructor() {
        this.init();
    }
    
    init() {
        console.log('EMR Assistant content script loaded');
        
        // Listen for messages from background script
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
        });
        
        // Set up page monitoring if needed
        this.setupPageMonitoring();
    }
    
    setupPageMonitoring() {
        // Monitor for page changes that might be relevant
        // This could be used to detect EMR-specific interactions
        
        // Example: Monitor for navigation events
        window.addEventListener('beforeunload', () => {
            // Page is about to unload
            console.log('Page unloading');
        });
        
        // Example: Monitor for DOM changes
        const observer = new MutationObserver((mutations) => {
            // Handle DOM changes if needed
            // This could be used to detect when medical data is loaded
        });
        
        // Start observing
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    handleMessage(message, sender, sendResponse) {
        switch (message.action) {
            case 'getPageInfo':
                sendResponse({
                    url: window.location.href,
                    title: document.title,
                    timestamp: Date.now()
                });
                break;
                
            case 'extractPageData':
                // Extract relevant data from the page
                const pageData = this.extractPageData();
                sendResponse({
                    success: true,
                    data: pageData
                });
                break;
                
            default:
                sendResponse({
                    success: false,
                    error: 'Unknown action'
                });
        }
    }
    
    extractPageData() {
        // Extract relevant data from the current page
        // This could be used to understand the context of screenshots
        
        return {
            url: window.location.href,
            title: document.title,
            timestamp: Date.now(),
            // Add more page-specific data extraction as needed
        };
    }
}

// Initialize content script
new ContentScriptManager(); 