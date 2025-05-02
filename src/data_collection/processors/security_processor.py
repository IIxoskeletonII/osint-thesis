"""Security processor for OSINT data."""

import re
import logging
from typing import Dict, Any, List, Set, Optional

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)

class SecurityProcessor(BaseProcessor):
    """Processor for security-related content extraction and enhancement."""
    
    # Common security-related patterns
    PATTERNS = {
        "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "url": r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*',
        "md5_hash": r'\b[a-fA-F0-9]{32}\b',
        "sha1_hash": r'\b[a-fA-F0-9]{40}\b',
        "sha256_hash": r'\b[a-fA-F0-9]{64}\b',
        "cve_id": r'CVE-\d{4}-\d{4,7}',
        "domain": r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    }
    
    # Security-related terminology for detection
    SECURITY_TERMS = {
        'vulnerability', 'exploit', 'malware', 'ransomware', 'phishing', 'attack', 
        'threat', 'security', 'breach', 'backdoor', 'botnet', 'compromise', 
        'credential', 'cryptography', 'cyber', 'encryption', 'exploit', 'firewall', 
        'incident', 'intrusion', 'keylogger', 'malicious', 'mitigation', 'payload', 
        'penetration', 'remediation', 'risk', 'rootkit', 'spyware', 'trojan', 
        'virus', 'vulnerability', 'worm', 'zero-day'
    }
    
    def __init__(self, processor_name: str = "security_processor"):
        """
        Initialize the security processor.
        
        Args:
            processor_name: Identifier for the processor
        """
        super().__init__(processor_name)
    
    def process(self, document: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process a document to extract security-related information.
        
        Args:
            document: Dictionary containing document content and metadata
            **kwargs: Additional parameters:
                - extract_indicators: Whether to extract IoCs (default: True)
                - score_security_relevance: Whether to calculate security relevance score (default: True)
                - extract_cves: Whether to specifically extract CVE IDs (default: True)
                
        Returns:
            Processed document with security information
        """
        self.logger.info(f"Processing document with security processor")
        
        content = document.get("content", "")
        if not content:
            self.logger.warning("Document has no content to process")
            return document
        
        extract_indicators = kwargs.get('extract_indicators', True)
        score_security_relevance = kwargs.get('score_security_relevance', True)
        extract_cves = kwargs.get('extract_cves', True)
        
        security_metadata = {}
        
        # Extract indicators of compromise
        if extract_indicators:
            indicators = self._extract_indicators(content)
            if indicators:
                security_metadata["indicators"] = indicators
        
        # Extract CVEs specifically
        if extract_cves:
            cves = self._extract_cves(content)
            if cves:
                security_metadata["cves"] = cves
        
        # Calculate security relevance score
        if score_security_relevance:
            security_score = self._calculate_security_relevance(content)
            security_metadata["security_relevance_score"] = security_score
        
        # Update document with security information
        processed_document = document.copy()
        processed_document["metadata"] = self._update_metadata(
            document.get("metadata", {}),
            {"security_metadata": security_metadata}
        )
        
        return processed_document
    
    def _extract_indicators(self, content: str) -> Dict[str, List[str]]:
        """Extract indicators of compromise from text."""
        indicators = {}
        
        for indicator_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                # Remove duplicates while preserving order
                unique_matches = list(dict.fromkeys(matches))
                indicators[indicator_type] = unique_matches
        
        return indicators
    
    def _extract_cves(self, content: str) -> List[Dict[str, Any]]:
        """Extract CVE IDs and surrounding context."""
        cves = []
        cve_pattern = r'CVE-\d{4}-\d{4,7}'
        matches = re.finditer(cve_pattern, content)
        
        for match in matches:
            cve_id = match.group(0)
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(content), match.end() + 100)
            context = content[start_pos:end_pos]
            
            cves.append({
                "cve_id": cve_id,
                "context": context.strip()
            })
        
        return cves
    
    def _calculate_security_relevance(self, content: str) -> float:
        """
        Calculate a security relevance score based on terminology presence.
        
        Returns a score between 0.0 and 1.0, where higher values indicate
        greater security relevance.
        """
        content_lower = content.lower()
        
        # Count security terms
        term_count = 0
        for term in self.SECURITY_TERMS:
            term_count += content_lower.count(term)
        
        # Count security indicators
        indicator_count = 0
        for pattern in self.PATTERNS.values():
            indicator_count += len(re.findall(pattern, content))
        
        # Calculate score based on term density and indicator presence
        # This is a simplified scoring mechanism
        content_length = len(content)
        if content_length == 0:
            return 0.0
        
        term_density = min(1.0, term_count / (content_length / 100)) * 0.7
        indicator_factor = min(1.0, indicator_count / 5) * 0.3
        
        return round(term_density + indicator_factor, 2)