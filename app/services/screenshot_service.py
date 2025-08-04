import logging
from datetime import datetime
from typing import List, Optional
from ..core.change_detection import ChangeDetector
from ..models.screenshot import Screenshot

logger = logging.getLogger(__name__)


class ScreenshotService:
    """Handles screenshot storage and management"""
    
    def __init__(self, max_screenshots: int = 200, change_detection_threshold: int = 8):
        self.max_screenshots = max_screenshots
        self.screenshots: List[Screenshot] = []
        self.change_detector = ChangeDetector(change_detection_threshold)
        self.enable_change_detection = True
        self.logger = logger
    
    def add_screenshot(self, screenshot_data: str, metadata: dict) -> dict:
        """Add a new screenshot with change detection"""
        try:
            # Check for visual changes if change detection is enabled
            has_significant_change = True
            change_detection_result = None
            
            if self.enable_change_detection and len(self.screenshots) > 0:
                # Get the most recent screenshot for comparison
                previous_screenshot = self.screenshots[-1]
                previous_data = previous_screenshot.image_data
                
                # Perform change detection
                has_significant_change = self.change_detector.detect_change(screenshot_data, previous_data)
                change_detection_result = {
                    'detected_change': has_significant_change,
                    'threshold': self.change_detector.threshold
                }
                
                if not has_significant_change:
                    self.logger.info(f"No significant change detected for screenshot {metadata.get('id')}")
                    return {
                        'success': True,
                        'id': metadata.get('id'),
                        'total_screenshots': len(self.screenshots),
                        'message': 'Screenshot skipped - no significant change detected',
                        'change_detection': change_detection_result
                    }
            
            # Create screenshot object
            screenshot = Screenshot(
                id=metadata.get('id'),
                image_data=screenshot_data,
                timestamp=datetime.fromtimestamp(metadata.get('timestamp', datetime.now().timestamp()) / 1000),
                url=metadata.get('url', ''),
                title=metadata.get('title', ''),
                quality=metadata.get('quality', 0.8),
                size=metadata.get('size', 0),
                has_significant_change=has_significant_change
            )
            
            # Add to storage
            self.screenshots.append(screenshot)
            
            # Remove oldest if we exceed limit
            if len(self.screenshots) > self.max_screenshots:
                removed = self.screenshots.pop(0)
                self.logger.info(f"Removed oldest screenshot: {removed.id}")
            
            self.logger.info(f"Screenshot uploaded successfully: {screenshot.id}")
            self.logger.info(f"Total screenshots stored: {len(self.screenshots)}")
            
            return {
                'success': True,
                'id': screenshot.id,
                'total_screenshots': len(self.screenshots),
                'message': 'Screenshot uploaded successfully',
                'change_detection': change_detection_result
            }
            
        except Exception as e:
            self.logger.error(f"Error adding screenshot: {str(e)}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def get_screenshots(self) -> List[dict]:
        """Get all screenshots as dictionaries"""
        return [screenshot.to_dict() for screenshot in self.screenshots]
    
    def get_stats(self) -> dict:
        """Get service statistics"""
        return {
            'screenshots_stored': len(self.screenshots),
            'max_screenshots': self.max_screenshots,
            'available_space': self.max_screenshots - len(self.screenshots),
            'change_detection_enabled': self.enable_change_detection,
            'change_detection_threshold': self.change_detector.threshold
        }
    
    def clear_screenshots(self) -> dict:
        """Clear all screenshots"""
        count = len(self.screenshots)
        self.screenshots = []
        self.logger.info(f"Cleared {count} screenshots")
        return {
            'success': True,
            'message': f'Cleared {count} screenshots'
        }
    
    def update_change_detection_settings(self, enabled: Optional[bool] = None, threshold: Optional[int] = None) -> dict:
        """Update change detection settings"""
        if enabled is not None:
            self.enable_change_detection = enabled
        if threshold is not None:
            self.change_detector.threshold = threshold
        
        return {
            'enabled': self.enable_change_detection,
            'threshold': self.change_detector.threshold
        } 