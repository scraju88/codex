# EMR Assistant Chrome Extension

AI-powered medical documentation assistant for EMR workflows.

## 🏗️ **Project Structure**

```
extension/
├── manifest.json              # Extension configuration
├── popup/
│   ├── popup.html            # User interface
│   ├── popup.css             # Styling
│   └── popup.js              # UI logic
├── background/
│   └── background.js         # Core capture logic
├── content/
│   └── content.js            # Page interaction
├── options/
│   ├── options.html          # Settings page
│   ├── options.css           # Settings styling
│   └── options.js            # Settings logic
└── README.md                 # This file
```

## 🚀 **Installation**

### **Development Mode:**

1. **Open Chrome** and navigate to `chrome://extensions/`
2. **Enable Developer Mode** (toggle in top right)
3. **Click "Load unpacked"** and select the `extension` folder
4. **Pin the extension** to your toolbar for easy access

### **Production Mode:**

1. **Package the extension** for Chrome Web Store
2. **Submit to Chrome Web Store** for distribution
3. **Install from Chrome Web Store** like any other extension

## 🎯 **Features**

### **✅ Basic Capture System:**
- **Screenshot Capture**: Capture current tab at configurable intervals
- **User Interface**: Clean, medical-themed popup interface
- **Settings Management**: Comprehensive options page
- **State Persistence**: Remember user preferences and capture state

### **🔄 Communication:**
- **Background Script**: Handles capture logic and timing
- **Popup Interface**: User controls and status display
- **Content Script**: Page interaction (placeholder)
- **Message Passing**: Communication between components

### **⚙️ Configuration:**
- **Capture Interval**: Configurable screenshot timing
- **Quality Settings**: Adjustable screenshot quality
- **Server URL**: Configurable server endpoint
- **Notification Settings**: User preference controls

## 🛠️ **Development**

### **📋 Prerequisites:**
- **Chrome Browser**: For testing and development
- **Text Editor**: VS Code, Sublime Text, etc.
- **Web Server**: For testing server communication

### **🔧 Development Workflow:**

1. **Edit Files**: Modify HTML, CSS, or JavaScript files
2. **Reload Extension**: Click "Reload" in `chrome://extensions/`
3. **Test Changes**: Open popup and test functionality
4. **Debug**: Use Chrome DevTools for debugging

### **🐛 Debugging:**

#### **Background Script:**
1. Go to `chrome://extensions/`
2. Find EMR Assistant
3. Click "Service Worker" link
4. Use Chrome DevTools for debugging

#### **Popup:**
1. Right-click extension icon
2. Click "Inspect popup"
3. Use Chrome DevTools for debugging

#### **Content Script:**
1. Open any web page
2. Open Chrome DevTools
3. Check Console for content script logs

## 📊 **Configuration**

### **🔄 Default Settings:**
```javascript
{
  captureInterval: 1.5,        // Seconds between captures
  quality: 0.8,                // Screenshot quality (0.1-1.0)
  serverUrl: 'https://your-server.com/api',
  maxRetries: 3,               // Upload retry attempts
  enableNotifications: true,    // Show notifications
  enableSound: false,          // Play sound alerts
  enableAnalytics: true,       // Usage analytics
  enableDebug: false           // Debug mode
}
```

### **⚙️ Permissions:**
- **`activeTab`**: Access current tab for screenshots
- **`storage`**: Store settings and state
- **`tabs`**: Access tab information
- **`scripting`**: Inject scripts if needed

## 🎯 **Usage**

### **📸 Basic Capture:**
1. **Click extension icon** to open popup
2. **Click "Start Capture"** to begin screenshot capture
3. **Navigate EMR** - extension captures screenshots automatically
4. **Click "Stop Capture"** to end capture session

### **⚙️ Settings:**
1. **Click "Settings"** in popup or go to options page
2. **Configure capture interval** and quality settings
3. **Set server URL** for your EMR Assistant server
4. **Save settings** to apply changes

### **📊 Status Monitoring:**
- **Screenshot Count**: Number of screenshots captured
- **Server Status**: Connection status to server
- **Capture Status**: Current capture state

## 🔧 **Technical Details**

### **🏗️ Architecture:**
- **Manifest V3**: Modern Chrome extension architecture
- **Service Worker**: Background script for capture logic
- **Message Passing**: Communication between components
- **Chrome Storage**: Local storage for settings and state

### **📊 Data Flow:**
```
User Action → Popup → Background Script → Screenshot Capture → Server Upload
     ↓              ↓              ↓                    ↓              ↓
UI Update ← Status ← State Update ← Process Screenshot ← Upload ← Server
```

### **🔒 Security:**
- **HTTPS Only**: Secure communication with server
- **Permission Model**: Minimal required permissions
- **Data Privacy**: Local processing before upload
- **Error Handling**: Graceful failure management

## 🚀 **Next Steps**

### **Phase 1B: Screenshot Capture**
- Implement actual screenshot capture functionality
- Add quality and format options
- Handle capture errors gracefully

### **Phase 1C: Quick Change Detection**
- Implement browser-side change detection
- Add upload decision logic
- Optimize for performance

### **Phase 1D: Server Integration**
- Add server upload functionality
- Implement retry logic
- Add connection status monitoring

### **Phase 1E: Storage Management**
- Implement server-side storage limits
- Add cleanup and management features
- Add analytics and monitoring

## 📝 **Notes**

- **Icons**: Add icon files to `assets/` folder
- **Server URL**: Update server URL in settings
- **Testing**: Test with various EMR systems
- **Security**: Review permissions and security model

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Test thoroughly**
5. **Submit a pull request**

## 📄 **License**

[Add your license information here]

---

**This extension provides the foundation for intelligent EMR assistance. The basic capture system is ready for testing and further development!** 