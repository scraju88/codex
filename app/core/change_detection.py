import numpy as np
from PIL import Image
import io
import base64
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Handles visual change detection"""
    
    def __init__(self, threshold: int = 8):
        self.threshold = threshold
        self.logger = logger
    
    def calculate_hash(self, screenshot_data: str) -> str:
        """Calculate perceptual hash for screenshot"""
        try:
            # Remove data URL prefix
            if screenshot_data.startswith('data:image/'):
                screenshot_data = screenshot_data.split(',')[1]
            
            # Decode base64 image
            img_data = base64.b64decode(screenshot_data)
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to grayscale
            img_gray = img.convert('L')
            
            # Multi-scale analysis: compare at different resolutions
            scales = [32, 64, 128]  # Different resolution levels
            hashes = []
            
            for scale in scales:
                # Resize image to current scale
                img_resized = img_gray.resize((scale, scale))
                img_array = np.array(img_resized)
                
                # Calculate mean and standard deviation for this scale
                mean_value = np.mean(img_array)
                std_value = np.std(img_array)
                
                # Create hash using both mean and std thresholds
                hash_bits = []
                for pixel in img_array.flatten():
                    if pixel > mean_value + std_value * 0.5:
                        hash_bits.append('1')
                    elif pixel < mean_value - std_value * 0.5:
                        hash_bits.append('0')
                    else:
                        hash_bits.append('2')  # Middle range
                
                hashes.append(''.join(hash_bits))
            
            # Combine hashes from all scales
            combined_hash = '|'.join(hashes)
            return combined_hash
            
        except Exception as e:
            self.logger.error(f"Error calculating screenshot hash: {e}")
            return ""
    
    def calculate_hash_difference(self, hash1: str, hash2: str) -> float:
        """Calculate the weighted difference between two multi-scale hashes"""
        if not hash1 or not hash2:
            return float('inf')
        
        try:
            # Split hashes by scale (separated by '|')
            scales1 = hash1.split('|')
            scales2 = hash2.split('|')
            
            if len(scales1) != len(scales2):
                return float('inf')
            
            total_difference = 0
            weights = [1.0, 0.7, 0.5]  # Weight different scales differently
            
            for i, (scale1, scale2) in enumerate(zip(scales1, scales2)):
                if len(scale1) != len(scale2):
                    continue
                
                # Calculate difference for this scale
                scale_diff = 0
                for a, b in zip(scale1, scale2):
                    if a != b:
                        # Weight differences based on the values
                        if a == '2' or b == '2':  # Middle range changes
                            scale_diff += 0.5
                        else:  # Binary changes
                            scale_diff += 1.0
                
                # Apply weight for this scale
                total_difference += scale_diff * weights[i]
            
            return total_difference
            
        except Exception as e:
            self.logger.error(f"Error calculating hash difference: {e}")
            return float('inf')
    
    def detect_change(self, current_data: str, previous_data: str) -> bool:
        """Detect if there's a significant visual change between screenshots"""
        current_hash = self.calculate_hash(current_data)
        previous_hash = self.calculate_hash(previous_data)
        
        if not current_hash or not previous_hash:
            self.logger.warning("Cannot compare hashes - assuming change")
            return True  # If we can't compare, assume there's a change
        
        # Calculate hash difference using multi-scale analysis
        difference = self.calculate_hash_difference(current_hash, previous_hash)
        
        # Use a lower threshold for more sensitive detection
        threshold = self.threshold * 0.5
        
        is_significant_change = difference > threshold
        
        if is_significant_change:
            self.logger.info(f"Visual change detected: {difference:.2f} difference (threshold: {threshold:.2f})")
        else:
            self.logger.debug(f"No significant change: {difference:.2f} difference (threshold: {threshold:.2f})")
        
        return is_significant_change 