"""
Validation utilities for complaint data
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Validation error severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Get validation summary"""
        issues = []
        if self.errors:
            issues.append(f"{len(self.errors)} errors")
        if self.warnings:
            issues.append(f"{len(self.warnings)} warnings")
        if self.info:
            issues.append(f"{len(self.info)} info")
        
        return ", ".join(issues) if issues else "Valid"


class ComplaintValidator:
    """Comprehensive complaint data validator"""
    
    def __init__(self):
        self.min_description_length = 10
        self.max_description_length = 2000
        self.max_file_size_mb = 10
        self.supported_image_types = ['jpg', 'jpeg', 'png', 'webp']
        self.supported_video_types = ['mp4', 'mov', 'avi']
        self.supported_document_types = ['pdf', 'doc', 'docx']
    
    def validate_classification_input(
        self,
        description: str,
        image_data: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> ValidationResult:
        """Validate input for complaint classification"""
        errors = []
        warnings = []
        info = []
        
        # Validate description
        if not description:
            errors.append("Description is required")
        else:
            desc_validation = self._validate_description(description)
            errors.extend(desc_validation.errors)
            warnings.extend(desc_validation.warnings)
            info.extend(desc_validation.info)
        
        # Validate image data
        if image_data:
            image_validation = self._validate_image_data(image_data)
            errors.extend(image_validation.errors)
            warnings.extend(image_validation.warnings)
            info.extend(image_validation.info)
        
        # Validate image URL
        if image_url:
            url_validation = self._validate_image_url(image_url)
            errors.extend(url_validation.errors)
            warnings.extend(url_validation.warnings)
            info.extend(url_validation.info)
        
        # Check if we have at least one valid input
        if not description and not image_data and not image_url:
            errors.append("At least description, image data, or image URL must be provided")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def validate_complaint_create(
        self,
        complaint_data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate complaint creation data"""
        errors = []
        warnings = []
        info = []
        
        # Required fields
        required_fields = ['user_id', 'title', 'description', 'location']
        for field in required_fields:
            if field not in complaint_data or not complaint_data[field]:
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate title
        if 'title' in complaint_data:
            title_validation = self._validate_title(complaint_data['title'])
            errors.extend(title_validation.errors)
            warnings.extend(title_validation.warnings)
        
        # Validate description
        if 'description' in complaint_data:
            desc_validation = self._validate_description(complaint_data['description'])
            errors.extend(desc_validation.errors)
            warnings.extend(desc_validation.warnings)
            info.extend(desc_validation.info)
        
        # Validate location
        if 'location' in complaint_data:
            location_validation = self._validate_location(complaint_data['location'])
            errors.extend(location_validation.errors)
            warnings.extend(location_validation.warnings)
            info.extend(location_validation.info)
        
        # Validate contact phone
        if 'contact_phone' in complaint_data and complaint_data['contact_phone']:
            phone_validation = self._validate_phone_number(complaint_data['contact_phone'])
            errors.extend(phone_validation.errors)
            warnings.extend(phone_validation.warnings)
        
        # Validate media URLs
        if 'media_urls' in complaint_data:
            media_validation = self._validate_media_urls(complaint_data['media_urls'])
            errors.extend(media_validation.errors)
            warnings.extend(media_validation.warnings)
        
        # Validate user-suggested category
        if 'category' in complaint_data and complaint_data['category']:
            category_validation = self._validate_category(complaint_data['category'])
            errors.extend(category_validation.errors)
            warnings.extend(category_validation.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _validate_title(self, title: str) -> ValidationResult:
        """Validate complaint title"""
        errors = []
        warnings = []
        info = []
        
        if not title:
            errors.append("Title cannot be empty")
            return ValidationResult(False, errors, warnings, info)
        
        if len(title) < 5:
            errors.append("Title must be at least 5 characters long")
        
        if len(title) > 200:
            warnings.append("Title is very long, consider shortening it")
        
        # Check for potential spam patterns
        spam_patterns = [
            r'^[A-Z\s]{20,}$',  # All caps
            r'(.)\1{4,}',       # Repeated characters
            r'^\d+$',           # All numbers
            r'^[!@#$%^&*()_+=\-\[\]{};:"\\|,.<>\/?]*$'  # All special chars
        ]
        
        for pattern in spam_patterns:
            if re.match(pattern, title):
                warnings.append("Title may be spam or invalid")
                break
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_description(self, description: str) -> ValidationResult:
        """Validate complaint description"""
        errors = []
        warnings = []
        info = []
        
        if not description:
            errors.append("Description cannot be empty")
            return ValidationResult(False, errors, warnings, info)
        
        description = description.strip()
        
        if len(description) < self.min_description_length:
            errors.append(f"Description must be at least {self.min_description_length} characters long")
        
        if len(description) > self.max_description_length:
            errors.append(f"Description cannot exceed {self.max_description_length} characters")
        
        # Check for meaningful content
        if len(description.split()) < 3:
            warnings.append("Description is very short, please provide more details")
        
        # Check for potential spam or inappropriate content
        spam_indicators = [
            'test', 'demo', 'sample', 'asdf', 'qwerty',
            'hello', 'hi', 'hey', 'ok', 'fine'
        ]
        
        words = description.lower().split()
        spam_count = sum(1 for word in words if word in spam_indicators)
        
        if spam_count > len(words) * 0.5:
            warnings.append("Description may contain test or spam content")
        
        # Language detection (simple)
        has_hindi = bool(re.search(r'[\u0900-\u097F]', description))
        has_english = bool(re.search(r'[a-zA-Z]', description))
        
        if has_hindi and has_english:
            info.append("Mixed language detected (Hindi + English)")
        elif has_hindi:
            info.append("Hindi language detected")
        elif has_english:
            info.append("English language detected")
        
        # Extract potential keywords for info
        keywords = self._extract_keywords(description)
        if keywords:
            info.append(f"Keywords detected: {', '.join(keywords[:5])}")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_location(self, location: Dict[str, Any]) -> ValidationResult:
        """Validate location data"""
        errors = []
        warnings = []
        info = []
        
        required_location_fields = ['lat', 'lng', 'address', 'ward_id']
        for field in required_location_fields:
            if field not in location or location[field] is None:
                errors.append(f"Location field '{field}' is required")
        
        # Validate coordinates
        if 'lat' in location and 'lng' in location:
            lat, lng = location['lat'], location['lng']
            
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                errors.append("Latitude and longitude must be numeric")
            else:
                if not (-90 <= lat <= 90):
                    errors.append("Latitude must be between -90 and 90")
                if not (-180 <= lng <= 180):
                    errors.append("Longitude must be between -180 and 180")
                
                # Check if coordinates are in reasonable range for India
                if not (6 <= lat <= 38) or not (68 <= lng <= 98):
                    warnings.append("Coordinates may be outside India")
        
        # Validate address
        if 'address' in location and location['address']:
            address = location['address'].strip()
            if len(address) < 10:
                warnings.append("Address seems too short")
            
            # Check for pincode
            pincode_pattern = r'\b\d{6}\b'
            if re.search(pincode_pattern, address):
                info.append("Pincode detected in address")
            else:
                warnings.append("Pincode not found in address")
        
        # Validate ward_id
        if 'ward_id' in location and location['ward_id']:
            ward_id = str(location['ward_id'])
            if not re.match(r'^[A-Za-z0-9_-]+$', ward_id):
                errors.append("Ward ID contains invalid characters")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_phone_number(self, phone: str) -> ValidationResult:
        """Validate phone number"""
        errors = []
        warnings = []
        info = []
        
        # Clean phone number
        clean_phone = re.sub(r'[^\d]', '', phone)
        
        if len(clean_phone) < 10:
            errors.append("Phone number must have at least 10 digits")
        elif len(clean_phone) > 15:
            errors.append("Phone number cannot exceed 15 digits")
        elif len(clean_phone) == 10:
            info.append("10-digit mobile number detected")
        elif len(clean_phone) > 10 and clean_phone.startswith('91'):
            info.append("Indian mobile number with country code detected")
        else:
            warnings.append("Unusual phone number format")
        
        # Check for valid Indian mobile patterns
        if len(clean_phone) == 10:
            if not clean_phone.startswith(('6', '7', '8', '9')):
                warnings.append("Indian mobile numbers usually start with 6, 7, 8, or 9")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_image_data(self, image_data: bytes) -> ValidationResult:
        """Validate image data"""
        errors = []
        warnings = []
        info = []
        
        if not image_data:
            errors.append("Image data is empty")
            return ValidationResult(False, errors, warnings, info)
        
        # Check file size
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > self.max_file_size_mb:
            errors.append(f"Image size ({size_mb:.1f}MB) exceeds maximum allowed size ({self.max_file_size_mb}MB)")
        elif size_mb > 5:
            warnings.append("Large image file, may affect processing time")
        
        # Check image type (from header bytes)
        image_type = self._detect_image_type(image_data)
        if image_type:
            if image_type.lower() not in self.supported_image_types:
                errors.append(f"Unsupported image type: {image_type}")
            else:
                info.append(f"Image type detected: {image_type}")
        else:
            errors.append("Unable to determine image type")
        
        # Check for valid image header
        if not self._is_valid_image_header(image_data):
            errors.append("Invalid image format or corrupted file")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_image_url(self, url: str) -> ValidationResult:
        """Validate image URL"""
        errors = []
        warnings = []
        info = []
        
        if not url:
            errors.append("Image URL is empty")
            return ValidationResult(False, errors, warnings, info)
        
        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url):
            errors.append("Invalid URL format")
        
        # Check for supported domains
        supported_domains = ['firebasestorage.googleapis.com', 'storage.googleapis.com']
        domain_match = any(domain in url for domain in supported_domains)
        if domain_match:
            info.append("Firebase Storage URL detected")
        else:
            warnings.append("URL may not be from a trusted source")
        
        # Check file extension
        ext_pattern = r'\.([a-zA-Z0-9]+)(?:\?|$)'
        match = re.search(ext_pattern, url)
        if match:
            ext = match.group(1).lower()
            if ext in self.supported_image_types:
                info.append(f"Image file extension: {ext}")
            elif ext in self.supported_video_types:
                warnings.append("Video file detected - video analysis not supported")
            elif ext in self.supported_document_types:
                warnings.append("Document file detected - document analysis not supported")
            else:
                warnings.append(f"Unknown file extension: {ext}")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_media_urls(self, media_urls: List[str]) -> ValidationResult:
        """Validate list of media URLs"""
        errors = []
        warnings = []
        info = []
        
        if not media_urls:
            return ValidationResult(True, errors, warnings, info)
        
        if len(media_urls) > 5:
            warnings.append("Too many media files - maximum 5 allowed")
        
        for i, url in enumerate(media_urls):
            url_validation = self._validate_image_url(url)
            for error in url_validation.errors:
                errors.append(f"Media {i+1}: {error}")
            for warning in url_validation.warnings:
                warnings.append(f"Media {i+1}: {warning}")
            for info_item in url_validation.info:
                info.append(f"Media {i+1}: {info_item}")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _validate_category(self, category: str) -> ValidationResult:
        """Validate complaint category"""
        errors = []
        warnings = []
        info = []
        
        valid_categories = [
            'water', 'sanitation', 'roads', 'electricity', 'housing',
            'waste', 'street_lights', 'drainage', 'eviction', 'noise', 'other'
        ]
        
        if category.lower() not in valid_categories:
            warnings.append(f"Unknown category: {category}")
        
        return ValidationResult(True, errors, warnings, info)
    
    def _detect_image_type(self, image_data: bytes) -> Optional[str]:
        """Detect image type from header bytes"""
        if not image_data:
            return None
        
        # Common image signatures
        signatures = {
            b'\xFF\xD8\xFF': 'jpeg',
            b'\x89PNG\r\n\x1a\n': 'png',
            b'RIFF': 'webp',  # WebP files start with RIFF
            b'GIF87a': 'gif',
            b'GIF89a': 'gif',
            b'BM': 'bmp'
        }
        
        for signature, img_type in signatures.items():
            if image_data.startswith(signature):
                return img_type
        
        return None
    
    def _is_valid_image_header(self, image_data: bytes) -> bool:
        """Check if image has valid header"""
        if not image_data or len(image_data) < 8:
            return False
        
        # Check for common image headers
        valid_headers = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'RIFF',  # WebP/AVI
            b'GIF87a',  # GIF
            b'GIF89a',  # GIF
            b'BM'  # BMP
        ]
        
        return any(image_data.startswith(header) for header in valid_headers)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as',
            'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
            'her', 'our', 'their', 'its', 'who', 'whom', 'whose',
            'what', 'where', 'when', 'why', 'how', 'all', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'now', 'here', 'there', 'then',
            'again', 'further', 'once', 'however', 'therefore', 'thus',
            'mere', 'sir', 'please', 'help', 'problem', 'issue'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return list(set(keywords))
