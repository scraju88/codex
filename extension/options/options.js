// EMR Assistant Options JavaScript
class OptionsManager {
    constructor() {
        this.elements = {};
        this.defaultSettings = {
            captureInterval: 1.5,
            quality: 0.8,
            serverUrl: 'https://your-server.com/api',
            maxRetries: 3,
            enableNotifications: true,
            enableSound: false,
            enableAnalytics: true,
            enableDebug: false
        };
        
        this.init();
    }
    
    init() {
        this.getElements();
        this.bindEvents();
        this.loadSettings();
    }
    
    getElements() {
        this.elements = {
            form: document.getElementById('settingsForm'),
            captureInterval: document.getElementById('captureInterval'),
            quality: document.getElementById('quality'),
            serverUrl: document.getElementById('serverUrl'),
            maxRetries: document.getElementById('maxRetries'),
            enableNotifications: document.getElementById('enableNotifications'),
            enableSound: document.getElementById('enableSound'),
            enableAnalytics: document.getElementById('enableAnalytics'),
            enableDebug: document.getElementById('enableDebug'),
            resetBtn: document.getElementById('resetBtn'),
            status: document.getElementById('status'),
            statusText: document.getElementById('statusText')
        };
    }
    
    bindEvents() {
        // Form submission
        this.elements.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });
        
        // Reset button
        this.elements.resetBtn.addEventListener('click', () => {
            this.resetToDefaults();
        });
        
        // Real-time validation
        this.elements.serverUrl.addEventListener('blur', () => {
            this.validateServerUrl();
        });
        
        this.elements.captureInterval.addEventListener('blur', () => {
            this.validateCaptureInterval();
        });
    }
    
    async loadSettings() {
        try {
            // Get current settings from background script
            const response = await this.sendMessage({ action: 'getSettings' });
            
            if (response.success) {
                const settings = response.data;
                
                // Populate form fields
                this.elements.captureInterval.value = settings.captureInterval || this.defaultSettings.captureInterval;
                this.elements.quality.value = settings.quality || this.defaultSettings.quality;
                this.elements.serverUrl.value = settings.serverUrl || this.defaultSettings.serverUrl;
                this.elements.maxRetries.value = settings.maxRetries || this.defaultSettings.maxRetries;
                this.elements.enableNotifications.checked = settings.enableNotifications !== false;
                this.elements.enableSound.checked = settings.enableSound || false;
                this.elements.enableAnalytics.checked = settings.enableAnalytics !== false;
                this.elements.enableDebug.checked = settings.enableDebug || false;
                
            } else {
                // Use default settings if failed to load
                this.populateDefaults();
            }
        } catch (error) {
            console.error('Error loading settings:', error);
            this.populateDefaults();
            this.showStatus('Failed to load settings. Using defaults.', 'error');
        }
    }
    
    populateDefaults() {
        this.elements.captureInterval.value = this.defaultSettings.captureInterval;
        this.elements.quality.value = this.defaultSettings.quality;
        this.elements.serverUrl.value = this.defaultSettings.serverUrl;
        this.elements.maxRetries.value = this.defaultSettings.maxRetries;
        this.elements.enableNotifications.checked = this.defaultSettings.enableNotifications;
        this.elements.enableSound.checked = this.defaultSettings.enableSound;
        this.elements.enableAnalytics.checked = this.defaultSettings.enableAnalytics;
        this.elements.enableDebug.checked = this.defaultSettings.enableDebug;
    }
    
    async saveSettings() {
        try {
            // Collect form data
            const settings = {
                captureInterval: parseFloat(this.elements.captureInterval.value),
                quality: parseFloat(this.elements.quality.value),
                serverUrl: this.elements.serverUrl.value.trim(),
                maxRetries: parseInt(this.elements.maxRetries.value),
                enableNotifications: this.elements.enableNotifications.checked,
                enableSound: this.elements.enableSound.checked,
                enableAnalytics: this.elements.enableAnalytics.checked,
                enableDebug: this.elements.enableDebug.checked
            };
            
            // Validate settings
            if (!this.validateSettings(settings)) {
                return;
            }
            
            // Send to background script
            const response = await this.sendMessage({
                action: 'updateSettings',
                settings: settings
            });
            
            if (response.success) {
                this.showStatus('Settings saved successfully!', 'success');
            } else {
                this.showStatus('Failed to save settings: ' + (response.error || 'Unknown error'), 'error');
            }
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showStatus('Failed to save settings. Please try again.', 'error');
        }
    }
    
    validateSettings(settings) {
        // Validate capture interval
        if (settings.captureInterval < 1 || settings.captureInterval > 60) {
            this.showStatus('Capture interval must be between 1 and 60 seconds.', 'error');
            return false;
        }
        
        // Validate quality
        if (settings.quality < 0.1 || settings.quality > 1.0) {
            this.showStatus('Quality must be between 0.1 and 1.0.', 'error');
            return false;
        }
        
        // Validate server URL
        if (!this.isValidUrl(settings.serverUrl)) {
            this.showStatus('Please enter a valid server URL.', 'error');
            return false;
        }
        
        // Validate max retries
        if (settings.maxRetries < 1 || settings.maxRetries > 10) {
            this.showStatus('Max retries must be between 1 and 10.', 'error');
            return false;
        }
        
        return true;
    }
    
    validateServerUrl() {
        const url = this.elements.serverUrl.value.trim();
        if (url && !this.isValidUrl(url)) {
            this.elements.serverUrl.style.borderColor = '#dc3545';
            this.showStatus('Please enter a valid server URL.', 'error');
        } else {
            this.elements.serverUrl.style.borderColor = '#e9ecef';
            this.hideStatus();
        }
    }
    
    validateCaptureInterval() {
        const interval = parseFloat(this.elements.captureInterval.value);
        if (interval < 1 || interval > 60) {
            this.elements.captureInterval.style.borderColor = '#dc3545';
            this.showStatus('Capture interval must be between 1 and 60 seconds.', 'error');
        } else {
            this.elements.captureInterval.style.borderColor = '#e9ecef';
            this.hideStatus();
        }
    }
    
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
    
    async resetToDefaults() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            this.populateDefaults();
            await this.saveSettings();
            this.showStatus('Settings reset to defaults.', 'success');
        }
    }
    
    showStatus(message, type = 'info') {
        this.elements.statusText.textContent = message;
        this.elements.status.className = `status show ${type}`;
        
        // Auto-hide success messages after 3 seconds
        if (type === 'success') {
            setTimeout(() => {
                this.hideStatus();
            }, 3000);
        }
    }
    
    hideStatus() {
        this.elements.status.className = 'status';
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
}

// Initialize options when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new OptionsManager();
}); 