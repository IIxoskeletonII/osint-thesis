from typing import Dict, Any, Optional, List
import logging
import re

logger = logging.getLogger(__name__)

class QueryProcessor:
    """
    Processes user queries for the OSINT system.
    Handles query interpretation, intent recognition, and query enhancement.
    """
    
    def __init__(self, rag_pipeline=None):
        """
        Initialize the query processor.
        
        Args:
            rag_pipeline: The RAG pipeline for knowledge retrieval
        """
        self.rag_pipeline = rag_pipeline
        logger.info("QueryProcessor initialized")
        
    def process_query(self, query: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a user query to determine intent and execution strategy.
        
        Args:
            query: The user's query text
            conversation_history: Previous conversation context
            
        Returns:
            Dict containing query analysis results
        """
        # Extract query type and focus
        query_type = self._determine_query_type(query)
        
        # Identify entities mentioned in the query
        entities = self._extract_entities(query)
        
        # Determine if query should use agent or direct RAG
        use_agent = self._should_use_agent(query, query_type)
        
        # Enhance query based on conversation history if needed
        enhanced_query = self._enhance_query(query, conversation_history)
        
        # Analyze query complexity
        complexity = self._determine_complexity(query)
        
        # Identify the domain focus of the query
        domain_focus = self._identify_domain_focus(query)
        
        return {
            "original_query": query,
            "enhanced_query": enhanced_query,
            "query_type": query_type,
            "entities": entities,
            "use_agent": use_agent,
            "complexity": complexity,
            "domain_focus": domain_focus
        }
    
    def _determine_query_type(self, query: str) -> str:
        """
        Determine the type of query based on content and structure.
        
        Args:
            query: The user's query text
            
        Returns:
            The identified query type
        """
        query = query.lower()
        
        # Improved pattern matching for query types
        if re.search(r'\b(what|who|where|when|which|explain|describe|tell me about|definition|define)\b', query):
            return "informational"
        elif re.search(r'\b(how to|how do|steps|guide|process|method|instructions|procedure)\b', query):
            return "procedural"
        elif re.search(r'\b(analyze|investigate|research|connections|explore|examine|assess|evaluate|why)\b', query):
            return "analytical"
        elif re.search(r'\b(compare|comparison|versus|vs|difference|similarities|better|worse|pros|cons)\b', query):
            return "comparative"
        elif re.search(r'\b(list|examples|top|best|worst|recommend|suggestion)\b', query):
            return "listing"
        elif len(query.split()) <= 3 and not re.search(r'\?', query):
            return "keyword"
        else:
            return "general"
    
    def _extract_entities(self, query: str) -> List[str]:
        """
        Extract potential security-related entities from the query.
        This is a simplified version - would use NER in production.
        
        Args:
            query: The user's query text
            
        Returns:
            List of extracted entities
        """
        # Enhanced security pattern recognition
        entity_patterns = [
            r"CVE-\d{4}-\d{4,7}", # CVE IDs
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IPv4
            r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",  # MAC address
            r"(http|https)://[^\s]+",  # URLs
            r"\b([0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\b",  # MD5/SHA1/SHA256
            r"\b(Mitre|ATT&CK|T\d{4}|TA\d{4})\b"  # MITRE ATT&CK
        ]
        
        entities = []
        for pattern in entity_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    entities.extend([m[0] for m in matches])
                else:
                    entities.extend(matches)
        
        # Extract key cybersecurity terms
        security_terms = [
            r"\b(malware|ransomware|spyware|trojan|virus|worm|botnet)\b",
            r"\b(phishing|spear-phishing|whaling|vishing|smishing)\b",
            r"\b(vulnerability|exploit|zero-day|patch|mitigation)\b",
            r"\b(firewall|IDS|IPS|EDR|XDR|SIEM|SOC)\b",
            r"\b(encryption|decryption|cryptography|cipher|hash)\b"
        ]
        
        for pattern in security_terms:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities.extend(matches)
        
        # Extract potential named entities (improved)
        # Look for capitalized words that might be product names, frameworks, or tools
        for word in re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', query):
            # Remove any trailing punctuation
            clean_word = re.sub(r'[^\w]$', '', word)
            if len(clean_word) > 1:  # Avoid single letters
                entities.append(clean_word)
                
        return list(set(entities))
    
    def _should_use_agent(self, query: str, query_type: str) -> bool:
        """
        Determine if the query should be processed by the agent framework.
        
        Args:
            query: The user's query text
            query_type: The identified query type
            
        Returns:
            Boolean indicating if agent should be used
        """
        # Improved agent usage determination
        
        # Always use agent for analytical queries
        if query_type == "analytical":
            return True
        
        # Use agent for comparative queries (they need multi-step reasoning)
        if query_type == "comparative":
            return True
            
        # Complex queries that need multi-step processing use the agent
        complex_indicators = [
            "find connections", "analyze", "investigate", 
            "compare", "timeline", "relationship", "track",
            "multi-step", "comprehensive", "detailed analysis",
            "explain how", "why would", "what if", "scenario",
            "identify patterns", "correlate"
        ]
        
        if any(indicator in query.lower() for indicator in complex_indicators):
            return True
        
        # Queries with multiple security entities likely need agent
        security_entity_count = len(self._extract_entities(query))
        if security_entity_count >= 2:
            return True
            
        # Longer queries (>15 words) often benefit from agent analysis
        if len(query.split()) > 15:
            return True
            
        # Short informational or keyword queries can use direct RAG
        if query_type in ["informational", "keyword"] and len(query.split()) < 10:
            return False
            
        # By default, use the agent for better analysis
        return True
    
    def _enhance_query(self, query: str, conversation_history: List[Dict[str, Any]]) -> str:
        """
        Enhance the query using conversation context.
        
        Args:
            query: The original query
            conversation_history: Previous conversation context
            
        Returns:
            Enhanced query text
        """
        # Skip if this is the first query or history is very short
        if len(conversation_history) < 2:
            return query
        
        # Get recent messages
        recent_msgs = conversation_history[-4:]  # Last 4 messages
        
        # Check for potential references to previous conversation
        pronoun_pattern = r'\b(it|this|that|they|them|those|these)\b'
        contains_pronouns = re.search(pronoun_pattern, query.lower())
        
        if contains_pronouns:
            # Find the most recent user query (excluding the current one)
            recent_user_queries = [msg["content"] for msg in conversation_history[:-1] 
                                  if msg["role"] == "user"]
            
            if recent_user_queries:
                previous_query = recent_user_queries[-1]
                # Add context from previous query
                return f"{query} (Context from previous query: {previous_query})"
        
        # If query seems like a follow-up
        if query.startswith(("And", "What about", "How about", "Also", "What if")):
            # Get the most recent system response
            recent_responses = [msg for msg in conversation_history if msg["role"] == "system"]
            if recent_responses:
                latest_response = recent_responses[-1]["content"]
                # Extract first sentence of the response for context
                first_sentence = latest_response.split('.')[0] + "."
                return f"{query} (Regarding: {first_sentence})"
        
        return query
    
    def _determine_complexity(self, query: str) -> str:
        """
        Determine the complexity of the query.
        
        Args:
            query: The user's query text
            
        Returns:
            Complexity level: "simple", "moderate", or "complex"
        """
        # Count words, entities, and technical terms
        word_count = len(query.split())
        entity_count = len(self._extract_entities(query))
        
        # Check for complex question patterns
        has_multiple_questions = len(re.findall(r'\?', query)) > 1
        has_compound_sentence = len(re.findall(r'\b(and|but|or|however|although|despite|while)\b', query.lower())) > 1
        
        # Assign complexity level
        if word_count > 25 or entity_count > 3 or has_multiple_questions or has_compound_sentence:
            return "complex"
        elif word_count > 10 or entity_count > 1:
            return "moderate"
        else:
            return "simple"
    
    def _identify_domain_focus(self, query: str) -> str:
        """
        Identify the cybersecurity domain focus of the query.
        
        Args:
            query: The user's query text
            
        Returns:
            Domain focus category
        """
        query_lower = query.lower()
        
        # Domain categories with associated keywords
        domains = {
            "threat_intel": ["threat", "actor", "campaign", "apt", "attack", "tactics", "techniques", "procedures", "ttp", "ioc", "indicator"],
            "vulnerability": ["vulnerability", "cve", "exploit", "patch", "mitigation", "zero-day", "weakness", "remediation"],
            "malware": ["malware", "ransomware", "virus", "trojan", "worm", "spyware", "botnet", "payload", "backdoor"],
            "network_security": ["network", "firewall", "ids", "ips", "traffic", "packet", "dns", "ip", "port", "protocol"],
            "defense": ["defense", "protection", "detection", "prevention", "monitoring", "response", "incident", "soc", "security operations"],
            "compliance": ["compliance", "regulation", "standard", "framework", "policy", "governance", "audit", "assessment"],
            "identity": ["identity", "authentication", "authorization", "access", "password", "mfa", "2fa", "privilege", "account"]
        }
        
        # Count keyword matches for each domain
        domain_scores = {domain: 0 for domain in domains}
        
        for domain, keywords in domains.items():
            for keyword in keywords:
                if keyword in query_lower:
                    domain_scores[domain] += 1
        
        # Return the domain with the highest score, or "general" if no matches
        if max(domain_scores.values(), default=0) > 0:
            return max(domain_scores.items(), key=lambda x: x[1])[0]
        else:
            return "general"