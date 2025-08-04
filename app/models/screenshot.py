from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import base64
import io
from PIL import Image


@dataclass
class Screenshot:
    """Screenshot data model"""
    id: str
    image_data: str  # Base64 encoded data URL
    timestamp: datetime
    url: str
    title: str
    quality: float
    size: int
    has_significant_change: bool = True
    
    def to_base64(self) -> str:
        """Convert to base64 string"""
        if self.image_data.startswith('data:image/'):
            return self.image_data.split(',')[1]
        return self.image_data
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'image_data': self.to_base64(),  # Return full base64 data
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'title': self.title,
            'quality': self.quality,
            'size': self.size,
            'has_significant_change': self.has_significant_change
        } 