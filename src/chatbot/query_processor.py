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
        query_type = self._determine_query_type(query) # Determine type first
        
        if query_type == "greeting":
            return {
                "original_query": query,
                "enhanced_query": query, 
                "query_type": "greeting",
                "entities": [],
                "use_agent": False, 
                "complexity": "simple",
                "domain_focus": "general"
            }

        entities = self._extract_entities(query)
        use_agent = self._should_use_agent(query, query_type)
        enhanced_query = self._enhance_query(query, conversation_history)
        complexity = self._determine_complexity(query)
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
        query_lower = query.lower().strip() # Ensure operations are on a consistent case and stripped
        
        greeting_patterns = [
            r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)$",
            r"^(hi|hello|hey) there!?$",
            r"^(how are you|how's it going|what's up)$" # Added more greeting variations
        ]
        for pattern in greeting_patterns:
            if re.fullmatch(pattern, query_lower):
                return "greeting"

        if re.search(r'\b(what|who|where|when|which|explain|describe|tell me about|definition|define)\b', query_lower):
            return "informational"
        elif re.search(r'\b(how to|how do|steps|guide|process|method|instructions|procedure)\b', query_lower):
            return "procedural"
        elif re.search(r'\b(analyze|investigate|research|connections|explore|examine|assess|evaluate|why)\b', query_lower):
            return "analytical"
        elif re.search(r'\b(compare|comparison|versus|vs|difference|similarities|better|worse|pros|cons)\b', query_lower):
            return "comparative"
        elif re.search(r'\b(list|examples|top|best|worst|recommend|suggestion)\b', query_lower):
            return "listing"
        elif len(query_lower.split()) <= 3 and not re.search(r'\?', query_lower):
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
        entity_patterns = [
            r"CVE-\d{4}-\d{4,7}", 
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 
            r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",
            r"(http|https)://[^\s\"']+", # Made URL matching more robust against trailing punctuation
            r"\b([0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\b",
            r"\b(Mitre|ATT&CK|T\d{4}(\.\d{3})?|TA\d{4})\b" # Improved MITRE pattern
        ]
        
        entities = []
        # Use original case query for extraction to preserve casing of entities like "Log4j"
        for pattern in entity_patterns:
            matches = re.findall(pattern, query) # Removed re.IGNORECASE here to preserve case
            if matches:
                # Handle tuples returned by some regex patterns (e.g., for MAC address)
                processed_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        processed_matches.append("".join(m for m in match if m)) # Join non-empty parts of tuple
                    else:
                        processed_matches.append(match)
                entities.extend(processed_matches)
        
        security_terms = [
            r"\b(malware|ransomware|spyware|trojan|virus|worm|botnet)\b",
            r"\b(phishing|spear-phishing|whaling|vishing|smishing)\b",
            r"\b(vulnerability|exploit|zero-day|patch|mitigation)\b",
            r"\b(firewall|IDS|IPS|EDR|XDR|SIEM|SOC)\b",
            r"\b(encryption|decryption|cryptography|cipher|hash)\b"
        ]
        
        for pattern in security_terms:
            matches = re.findall(pattern, query, re.IGNORECASE) # IGNORECASE is fine for these general terms
            if matches:
                entities.extend(matches)
        
        # Extract potential named entities (Capitalized words)
        # This might be too broad, consider refining if it picks up too much noise
        for word_match in re.finditer(r'\b([A-Z][a-zA-Z0-9_&.-]*)\b', query):
            word = word_match.group(1)
            # Avoid adding already found specific entities like CVEs or general terms
            if word not in entities and word.lower() not in [term.strip(r'\b()') for term_list in security_terms for term in term_list.split('|')]:
                 # Avoid single uppercase letters unless part of an acronym (e.g., "A" vs "APT")
                if len(word) > 1 or (len(word) == 1 and word.isupper()):
                    entities.append(word)
                
        return list(set(entities)) # Return unique entities
    
    def _should_use_agent(self, query: str, query_type: str) -> bool:
        """
        Determine if the query should be processed by the agent framework.
        """
        if query_type == "greeting": # Already handled in process_query, but good for explicitness
            return False

        query_lower = query.lower()
        
        if query_type in ["analytical", "comparative"]:
            return True
            
        complex_indicators = [
            "find connections", "analyze", "investigate", 
            "compare", "timeline", "relationship", "track",
            "multi-step", "comprehensive", "detailed analysis",
            "explain how", "why would", "what if", "scenario",
            "identify patterns", "correlate"
        ]
        
        if any(indicator in query_lower for indicator in complex_indicators):
            return True
        
        security_entity_count = len(self._extract_entities(query))
        if security_entity_count >= 2: # If multiple distinct entities, agent might be better for synthesis
            return True
            
        if len(query_lower.split()) > 15: # Longer queries often imply more complex intent
            return True
            
        if query_type in ["informational", "keyword"] and len(query_lower.split()) < 10 and security_entity_count < 2:
            return False # Simpler info requests can go to RAG directly
            
        return True # Default to agent for unclassified or potentially complex cases
    
    def _enhance_query(self, query: str, conversation_history: List[Dict[str, Any]]) -> str:
        """
        Enhance the query using conversation context.
        """
        if len(conversation_history) < 2: # Need at least one user query and one assistant response before enhancing
            return query
        
        # Consider only the last few turns for context relevance
        # Example: last 2 user messages and last 2 assistant responses
        relevant_history = conversation_history[-5:] # Consider up to the last message (which is the current user query)

        # Check for pronouns or anaphoric references in the current query
        pronoun_pattern = r'\b(it|this|that|they|them|those|these|its|their|theirs)\b'
        follow_up_phrases = [
            r"^(and )?what about", r"^(and )?how about", r"^(and )?tell me more about", 
            r"^also,", r"^what if", r"^in that case,"
        ]

        needs_context = False
        if re.search(pronoun_pattern, query.lower()):
            needs_context = True
        for phrase_pattern in follow_up_phrases:
            if re.match(phrase_pattern, query.lower()):
                needs_context = True
                break
        
        if needs_context:
            context_parts = []
            # Look for entities or key nouns in previous turns to resolve ambiguity
            # This is a simplified approach; true anaphora resolution is complex.
            for i in range(len(relevant_history) - 2, -1, -1): # Iterate backwards from message before current
                msg = relevant_history[i]
                if msg["role"] == "user":
                    # Extract entities from previous user query
                    prev_entities = self._extract_entities(msg["content"])
                    if prev_entities:
                        context_parts.append(f"Previously discussed: {', '.join(prev_entities[:2])}.") # Take first few
                        break # Often the most recent user query is most relevant
                elif msg["role"] == "assistant":
                    # Extract key nouns from previous assistant response (simplified)
                    # In a real system, you might summarize or extract topics
                    response_summary = " ".join(msg["content"].split()[:15]) + "..." # First 15 words
                    context_parts.append(f"Assistant previously mentioned: \"{response_summary}\".")
                    # Allow finding context from assistant if user's previous query wasn't rich
                    if len(context_parts) >=1: # Limit context length
                        break 
            
            if context_parts:
                return f"{query} (Considering previous context: {' '.join(reversed(context_parts))})"
        
        return query
    
    def _determine_complexity(self, query: str) -> str:
        """
        Determine the complexity of the query.
        """
        word_count = len(query.split())
        # Use a refined entity count for complexity; _extract_entities can be noisy for this
        # For complexity, let's count specific patterns more heavily
        specific_entity_patterns = [r"CVE-\d{4}-\d{4,7}", r"APT\d+"]
        specific_entity_count = 0
        for pattern in specific_entity_patterns:
            specific_entity_count += len(re.findall(pattern, query, re.IGNORECASE))

        has_multiple_questions = len(re.findall(r'\?', query)) > 1
        has_logical_operators = len(re.findall(r'\b(and|or|not|implies|if then)\b', query.lower())) > 0
        
        if word_count > 20 or specific_entity_count > 2 or has_multiple_questions or has_logical_operators:
            return "complex"
        elif word_count > 10 or specific_entity_count > 0:
            return "moderate"
        else:
            return "simple"
    
    def _identify_domain_focus(self, query: str) -> str:
        """
        Identify the cybersecurity domain focus of the query.
        """
        query_lower = query.lower()
        
        domains = {
            "threat_intel": ["threat actor", "apt", "campaign", "ttp", "indicator of compromise", "ioc"],
            "vulnerability_management": ["vulnerability", "cve", "exploit", "patch", "zero-day", "cvss", "remediation"],
            "malware_analysis": ["malware", "ransomware", "virus", "trojan", "backdoor", "payload", "obfuscation"],
            "network_security": ["network", "firewall", "ids", "ips", "traffic", "packet", "dns", "vpn", "segmentation"],
            "incident_response": ["incident", "breach", "response plan", "forensics", "containment", "eradication"],
            "security_tools": ["siem", "soc", "edr", "xdr", "scanner", "analyzer"],
            "authentication_identity": ["authentication", "identity", "mfa", "2fa", "password", "credential", "access control", "zkauth"],
            "cryptography_encryption": ["encryption", "cryptography", "cipher", "hash", "ssl", "tls", "pgp"],
            "osint_techniques": ["osint", "reconnaissance", "data collection", "social media intelligence", "dark web monitoring"]
        }
        
        domain_scores = {domain: 0 for domain in domains}
        
        for domain, keywords in domains.items():
            for keyword in keywords:
                # Use regex for whole word matching to avoid partial matches like "cat" in "catalog"
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    domain_scores[domain] += 1
        
        # If multiple domains have scores, pick the one with the highest score.
        # If scores are tied, it could be multi-domain or general.
        max_score = max(domain_scores.values(), default=0)
        if max_score > 0:
            # Get all domains with the max score
            top_domains = [domain for domain, score in domain_scores.items() if score == max_score]
            if len(top_domains) == 1:
                return top_domains[0]
            else:
                return "multi_domain" # Or could return a list: top_domains
        else:
            return "general_cybersecurity"