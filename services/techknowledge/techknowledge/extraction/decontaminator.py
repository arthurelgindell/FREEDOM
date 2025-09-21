"""
Technical Decontaminator
Removes all human behavioral elements from technical documentation
Preserves only pure technical facts
"""

import re
from typing import Dict, List, Tuple, Set, Any
import json
import hashlib
from dataclasses import dataclass
from ..core.config import HUMAN_CONTAMINATION_PATTERNS, TECHNICAL_PRESERVATION_PATTERNS


@dataclass
class DecontaminationResult:
    """Result of decontamination process"""
    original_text: str
    cleaned_text: str
    removed_lines: List[str]
    preserved_technical: List[str]
    contamination_score: float
    technical_score: float
    stats: Dict[str, Any]


class TechnicalDecontaminator:
    """Remove all human behavioral elements from technical documentation"""
    
    def __init__(self):
        """Initialize with compiled regex patterns for performance"""
        # Compile contamination patterns
        self.contamination_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in HUMAN_CONTAMINATION_PATTERNS
        ]
        
        # Compile technical patterns (case-sensitive for accuracy)
        self.technical_patterns = [
            re.compile(pattern) 
            for pattern in TECHNICAL_PRESERVATION_PATTERNS
        ]
        
        # Additional filters for common non-technical content
        self.skip_patterns = [
            re.compile(r'^\s*$'),  # Empty lines
            re.compile(r'^[\s\-=]+$'),  # Separator lines
            re.compile(r'^\s*#*\s*(table of contents|toc)\s*$', re.IGNORECASE),
            re.compile(r'^\s*#*\s*(introduction|getting started|overview)\s*$', re.IGNORECASE),
            re.compile(r'^\s*(copyright|license|disclaimer)', re.IGNORECASE),
        ]
    
    def decontaminate(self, text: str) -> DecontaminationResult:
        """
        Remove human elements, keep only technical facts
        
        Args:
            text: Raw documentation text
            
        Returns:
            DecontaminationResult with cleaned text and statistics
        """
        original_length = len(text)
        lines = text.split('\n')
        
        cleaned_lines = []
        removed_lines = []
        preserved_technical = []
        
        contamination_count = 0
        technical_count = 0
        
        for line in lines:
            # Skip empty or separator lines
            if any(pattern.match(line) for pattern in self.skip_patterns):
                continue
            
            # Check contamination level
            contamination_matches = sum(
                1 for pattern in self.contamination_patterns 
                if pattern.search(line)
            )
            
            # Check technical content
            technical_matches = sum(
                1 for pattern in self.technical_patterns 
                if pattern.search(line)
            )
            
            # Decision logic: Keep if technical and minimal contamination
            if technical_matches > 0 and contamination_matches == 0:
                # Pure technical content
                cleaned_lines.append(line)
                preserved_technical.append(line)
                technical_count += 1
            elif technical_matches > contamination_matches:
                # More technical than contaminated - try to clean
                cleaned_line = self._extract_technical_only(line)
                if cleaned_line and self._is_technical_enough(cleaned_line):
                    cleaned_lines.append(cleaned_line)
                    technical_count += 1
                else:
                    removed_lines.append(line)
                    contamination_count += 1
            else:
                # Too contaminated or not technical
                removed_lines.append(line)
                contamination_count += 1
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Calculate scores
        total_lines = len([l for l in lines if l.strip()])
        contamination_score = (contamination_count / total_lines) if total_lines > 0 else 0
        technical_score = (technical_count / total_lines) if total_lines > 0 else 0
        
        stats = {
            'original_lines': len(lines),
            'cleaned_lines': len(cleaned_lines),
            'removed_lines': len(removed_lines),
            'contamination_percentage': contamination_score * 100,
            'technical_percentage': technical_score * 100,
            'original_size': original_length,
            'cleaned_size': len(cleaned_text),
            'size_reduction': ((original_length - len(cleaned_text)) / original_length * 100) if original_length > 0 else 0
        }
        
        return DecontaminationResult(
            original_text=text,
            cleaned_text=cleaned_text,
            removed_lines=removed_lines[:10],  # Sample for logging
            preserved_technical=preserved_technical[:10],  # Sample
            contamination_score=contamination_score,
            technical_score=technical_score,
            stats=stats
        )
    
    def _extract_technical_only(self, line: str) -> str:
        """Extract only technical facts from a mixed line"""
        # Remove all contamination patterns
        cleaned = line
        for pattern in self.contamination_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Remove leading/trailing punctuation that might be left over
        cleaned = cleaned.strip(' .,;:')
        
        return cleaned if cleaned else ''
    
    def _is_technical_enough(self, line: str) -> bool:
        """Check if line contains enough technical content"""
        if len(line.strip()) < 10:  # Too short to be meaningful
            return False
        
        # Must match at least one technical pattern
        return any(pattern.search(line) for pattern in self.technical_patterns)
    
    def extract_technical_sections(self, text: str) -> Dict[str, List[str]]:
        """
        Extract and categorize technical content by type
        
        Returns:
            Dictionary with keys: 'apis', 'configs', 'types', 'limits', 'protocols'
        """
        result = self.decontaminate(text)
        lines = result.cleaned_text.split('\n')
        
        sections = {
            'apis': [],
            'configs': [],
            'types': [],
            'limits': [],
            'protocols': [],
            'versions': [],
            'errors': []
        }
        
        # Patterns for categorization
        api_pattern = re.compile(r'(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+/|function\s+\w+|method\s+\w+')
        config_pattern = re.compile(r'(parameter|option|flag|setting|config):\s*\w+|default:\s*\w+')
        type_pattern = re.compile(r'(type|interface|struct|class|enum)\s+\w+|:\s*(string|number|boolean|array|object)')
        limit_pattern = re.compile(r'(limit|maximum|minimum|constraint):\s*\d+|must be|cannot exceed')
        protocol_pattern = re.compile(r'(protocol|format|encoding|schema):\s*\w+|implements\s+\w+')
        version_pattern = re.compile(r'(version|v?)\d+\.?\d*\.?\d*|deprecated|removed in|since v?\d+')
        error_pattern = re.compile(r'(error|exception|status code):\s*\d+|throws\s+\w+|fails with')
        
        for line in lines:
            if api_pattern.search(line):
                sections['apis'].append(line)
            elif config_pattern.search(line):
                sections['configs'].append(line)
            elif type_pattern.search(line):
                sections['types'].append(line)
            elif limit_pattern.search(line):
                sections['limits'].append(line)
            elif protocol_pattern.search(line):
                sections['protocols'].append(line)
            elif version_pattern.search(line):
                sections['versions'].append(line)
            elif error_pattern.search(line):
                sections['errors'].append(line)
        
        # Remove empty sections
        return {k: v for k, v in sections.items() if v}
    
    def calculate_checksum(self, text: str) -> str:
        """Calculate checksum for change detection"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def validate_technical_purity(self, text: str) -> Tuple[bool, float]:
        """
        Validate if text meets technical purity standards
        
        Returns:
            (is_pure, purity_score)
        """
        result = self.decontaminate(text)
        
        # Must have high technical content and low contamination
        is_pure = (
            result.technical_score >= 0.5 and  # 50% technical minimum
            result.contamination_score <= 0.4   # 40% contamination maximum
        )
        
        # Purity score: technical minus contamination
        purity_score = result.technical_score - result.contamination_score
        
        return is_pure, purity_score
