"""
Image quality assessment for Mahjong tile recognition
Checks blur, brightness, contrast, and overall suitability before LLM processing
"""

import cv2
import numpy as np
import base64
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class ImageQualityResult:
    """Result of image quality assessment"""
    is_acceptable: bool
    blur_score: float
    brightness_score: float
    contrast_score: float
    sharpness_score: float
    issues: list
    recommendations: list

class ImageQualityChecker:
    """Comprehensive image quality assessment for Mahjong tile images"""
    
    def __init__(self):
        # Quality thresholds (tuned for Mahjong tile visibility)
        self.blur_threshold = 100.0  # Laplacian variance threshold
        self.min_brightness = 30     # Too dark (0-255 scale)
        self.max_brightness = 240    # Too bright/overexposed
        self.min_contrast = 20       # Too flat/low contrast
        self.min_resolution = (300, 300)  # Minimum pixel dimensions
        self.max_file_size = 10 * 1024 * 1024  # 10MB max
        
        logger.info("Image quality checker initialized")
    
    def decode_base64_image(self, base64_data: str) -> Optional[np.ndarray]:
        """Decode base64 image data to OpenCV format"""
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image'):
                base64_data = base64_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(base64_data)
            
            # Convert to PIL Image first for better format support
            pil_image = Image.open(BytesIO(image_bytes))
            
            # Convert PIL to RGB (in case it's RGBA, grayscale, etc.)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to OpenCV format (BGR)
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            return opencv_image
            
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            return None
    
    def check_blur(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Detect image blur using Laplacian variance
        Returns: (blur_score, is_sharp_enough)
        Higher score = sharper image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian variance (focus measure)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            is_sharp = laplacian_var >= self.blur_threshold
            
            return laplacian_var, is_sharp
            
        except Exception as e:
            logger.error(f"Blur detection failed: {e}")
            return 0.0, False
    
    def check_brightness(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Check image brightness/exposure
        Returns: (brightness_score, is_well_lit)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate mean brightness
            mean_brightness = np.mean(gray)
            
            # Check if within acceptable range
            is_well_lit = self.min_brightness <= mean_brightness <= self.max_brightness
            
            return mean_brightness, is_well_lit
            
        except Exception as e:
            logger.error(f"Brightness check failed: {e}")
            return 0.0, False
    
    def check_contrast(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Check image contrast (important for tile edge detection)
        Returns: (contrast_score, has_good_contrast)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate standard deviation as contrast measure
            contrast_score = np.std(gray)
            
            has_good_contrast = contrast_score >= self.min_contrast
            
            return contrast_score, has_good_contrast
            
        except Exception as e:
            logger.error(f"Contrast check failed: {e}")
            return 0.0, False
    
    def check_resolution(self, image: np.ndarray) -> Tuple[Tuple[int, int], bool]:
        """
        Check if image resolution is sufficient for tile recognition
        Returns: ((width, height), is_sufficient)
        """
        height, width = image.shape[:2]
        
        is_sufficient = (width >= self.min_resolution[0] and 
                        height >= self.min_resolution[1])
        
        return (width, height), is_sufficient
    
    def detect_tile_regions(self, image: np.ndarray) -> Tuple[int, bool]:
        """
        Attempt to detect rectangular regions that could be Mahjong tiles
        Returns: (potential_tile_count, likely_has_tiles)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours that could be tiles (rectangular, reasonable size)
            potential_tiles = 0
            min_area = 500  # Minimum area for a tile
            max_area = (image.shape[0] * image.shape[1]) // 4  # Max 1/4 of image
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    # Check if roughly rectangular
                    perimeter = cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
                    
                    # If it has 4 corners (roughly rectangular)
                    if len(approx) >= 4:
                        potential_tiles += 1
            
            likely_has_tiles = potential_tiles >= 1
            
            return potential_tiles, likely_has_tiles
            
        except Exception as e:
            logger.error(f"Tile detection failed: {e}")
            return 0, False
    
    def assess_quality(self, base64_image: str) -> ImageQualityResult:
        """
        Comprehensive image quality assessment
        Returns detailed quality analysis with recommendations
        """
        issues = []
        recommendations = []
        
        # Decode image
        image = self.decode_base64_image(base64_image)
        if image is None:
            return ImageQualityResult(
                is_acceptable=False,
                blur_score=0.0,
                brightness_score=0.0,
                contrast_score=0.0,
                sharpness_score=0.0,
                issues=["Failed to decode image"],
                recommendations=["Please upload a valid image file (JPEG, PNG, etc.)"]
            )
        
        # Check file size (approximate from base64)
        estimated_size = len(base64_image) * 0.75  # Base64 is ~133% of original
        if estimated_size > self.max_file_size:
            issues.append(f"Image too large ({estimated_size/1024/1024:.1f}MB)")
            recommendations.append("Please compress the image or take a smaller photo")
        
        # Resolution check
        (width, height), res_ok = self.check_resolution(image)
        if not res_ok:
            issues.append(f"Resolution too low ({width}x{height})")
            recommendations.append(f"Please use at least {self.min_resolution[0]}x{self.min_resolution[1]} resolution")
        
        # Blur detection
        blur_score, is_sharp = self.check_blur(image)
        if not is_sharp:
            issues.append(f"Image is blurry (sharpness: {blur_score:.1f})")
            recommendations.append("Please hold the camera steady and ensure the tiles are in focus")
        
        # Brightness check
        brightness_score, is_well_lit = self.check_brightness(image)
        if not is_well_lit:
            if brightness_score < self.min_brightness:
                issues.append(f"Image too dark (brightness: {brightness_score:.1f})")
                recommendations.append("Please take the photo in better lighting or use flash")
            else:
                issues.append(f"Image overexposed (brightness: {brightness_score:.1f})")
                recommendations.append("Please reduce lighting or move away from bright light sources")
        
        # Contrast check
        contrast_score, has_contrast = self.check_contrast(image)
        if not has_contrast:
            issues.append(f"Poor contrast (contrast: {contrast_score:.1f})")
            recommendations.append("Please ensure good lighting with clear tile edges visible")
        
        # Tile detection
        tile_count, has_tiles = self.detect_tile_regions(image)
        if not has_tiles:
            issues.append("No clear tile shapes detected")
            recommendations.append("Please ensure Mahjong tiles are clearly visible and well-framed")
        
        # Calculate overall sharpness score (combination of metrics)
        sharpness_score = min(100, max(0, (blur_score / self.blur_threshold) * 100))
        
        # Determine if image is acceptable
        is_acceptable = (is_sharp and is_well_lit and has_contrast and 
                        res_ok and has_tiles and estimated_size <= self.max_file_size)
        
        return ImageQualityResult(
            is_acceptable=is_acceptable,
            blur_score=blur_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            sharpness_score=sharpness_score,
            issues=issues,
            recommendations=recommendations
        )
    
    def get_quality_summary(self, result: ImageQualityResult) -> Dict:
        """Get a user-friendly summary of image quality"""
        if result.is_acceptable:
            return {
                "status": "good",
                "message": "Image quality is suitable for analysis",
                "sharpness": f"{result.sharpness_score:.0f}%"
            }
        else:
            return {
                "status": "poor",
                "message": "Image quality needs improvement",
                "issues": result.issues,
                "recommendations": result.recommendations,
                "sharpness": f"{result.sharpness_score:.0f}%"
            }

# Global image quality checker instance
image_quality_checker = ImageQualityChecker()