import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)

class AgentResponseHandler:
    """
    Handles the formatting and extraction of information from agent responses.
    """

    @staticmethod
    def extract_conclusion(agent_result: Dict[str, Any]) -> str:
        """
        Extract the conclusion from an agent result.
        Prioritizes 'response' field assuming it holds the final synthesized answer.
        """
        if not agent_result:
            return "No agent result provided."

        # Prioritize the 'response' field from the execute method's return value
        conclusion = agent_result.get("response")
        if conclusion and isinstance(conclusion, str) and len(conclusion.strip()) > 10: # Min length check
            # Check if it starts like a typical ReAct internal thought - if so, it's not final
            if conclusion.strip().startswith("Thought:") or conclusion.strip().startswith("Action:"):
                 logger.warning("Agent final response field looks like an internal thought/action, may be incomplete.")
                 # Fallback logic needed
            else:
                # Looks like a valid final answer
                return conclusion.strip()

        # Fallback: If 'response' is missing or short, check last thought if agent completed
        if agent_result.get("status") == "completed":
             thoughts = agent_result.get("thoughts", [])
             if thoughts:
                 last_thought = thoughts[-1]
                 # Avoid returning simple action plans as conclusions
                 if "action:" not in last_thought.lower() and "final answer:" not in last_thought.lower():
                      return f"Analysis based on last thought: {last_thought}"

        # Last resort messages based on status
        status = agent_result.get("status", "unknown")
        if status == "max_iterations_reached":
             return "Agent reached maximum analysis steps without providing a conclusive final answer. Review the conversation history for details."
        elif status == "completed":
             return "Agent processing complete, but a clear final answer could not be extracted from the response content."
        else: # Unknown or other error status
             return "Agent processing resulted in an unknown state or error."


    @staticmethod
    def _is_general_knowledge_response(agent_result: Dict[str, Any], conclusion: str, kb_search_successful: bool) -> bool:
        """
        Determine if the agent response appears to be based on general knowledge.
        Added more logging for debugging classification.
        """
        status = agent_result.get("status", "unknown")
        logger.debug(f"--- Inside _is_general_knowledge_response ---")
        logger.debug(f"Agent Status: {status}")
        logger.debug(f"KB Search Successful Flag: {kb_search_successful}")
        # logger.debug(f"Conclusion Text (start): {conclusion[:150]}...") # Optional: log conclusion start

        if status != "completed":
            logger.debug(f"Agent status is '{status}'. Checking if KB search was attempted...")
            if kb_search_successful:
                logger.debug("Agent incomplete, but KB search occurred. Treating as potentially grounded (returning False).")
                return False # Let's assume if search happened, it's not pure fallback even if incomplete
            else:
                logger.debug("Agent incomplete and NO KB search occurred. Returning True (Fallback).")
                return True

        if kb_search_successful:
            logger.debug("KB search was successful. Checking conclusion for denial indicators...")
            no_info_indicators = [
                "i cannot find specific information", "unable to provide specific details",
                "don't have specific information", "no specific details about this",
                "insufficient data in our knowledge base", "knowledge base does not contain",
                "i cannot locate any specific details", "search returned empty",
                "based on my search", "i couldn't find", "unable to find",
                "recommend consulting official sources", # Might indicate lack of specific KB info
                "based on my knowledge" # Explicitly mentions general knowledge
            ]
            conclusion_lower = conclusion.lower()
            found_denial_indicator = False
            matched_indicator = None
            for indicator in no_info_indicators:
                if indicator in conclusion_lower:
                    found_denial_indicator = True
                    matched_indicator = indicator
                    break

            if found_denial_indicator:
                logger.debug(f"Found denial indicator: '{matched_indicator}'. Checking for citations...")
                # Check for citations more reliably using the parsed_sources from agent_result
                source_citations = agent_result.get("parsed_sources", [])

                if not source_citations:
                    logger.debug("Conclusion denies finding info AND no sources were cited by agent. Returning True (Fallback).")
                    return True
                else:
                    logger.debug("Conclusion mentions lack of info BUT sources were cited/parsed. Returning False (Grounded).")
                    return False
            else:
                logger.debug("KB search done, conclusion does not contain strong denial indicators. Returning False (Grounded).")
                return False
        else:
            logger.debug("No successful KB search logged. Returning True (Fallback).")
            return True

    @staticmethod
    def format_agent_response(agent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format agent result into a standard response format.
        Improved logic for determining response type using status and KB search flag.
        """
        final_response_text = AgentResponseHandler.extract_conclusion(agent_result)
        actions_taken = agent_result.get("actions", [])
        status = agent_result.get("status", "unknown")
        parsed_sources_from_agent = agent_result.get("parsed_sources", []) # Get sources parsed by agent

        # Determine if a knowledge base search was successfully attempted
        actions_taken = agent_result.get("actions", [])
        # --->>> Add logging here <<<---
        logger.debug(f"Handler received actions_taken: {actions_taken}")
        kb_search_successful = any(
            action.get("action") == "search_kb" for action in actions_taken
        )
        # --->>> Add logging here <<<---
        logger.debug(f"Calculated kb_search_successful: {kb_search_successful}")


        # Determine if the response is likely general knowledge vs KB-grounded
        is_general_knowledge = AgentResponseHandler._is_general_knowledge_response(
            agent_result, final_response_text, kb_search_successful
        )

        # Determine Response Type and Confidence
        response_type = "agent" # Default
        confidence = 0.75 # Default

        final_sources = [] # Initialize final sources list

        if is_general_knowledge:
            response_type = "claude_fallback"
            confidence = 0.60
            final_sources = parsed_sources_from_agent or ["Claude general knowledge"] # Use parsed if LLM cited anyway
        elif status != "completed":
            confidence = 0.50
            response_type = "agent_incomplete"
            final_sources = parsed_sources_from_agent or ["Agent Analysis (Incomplete)"]
            if kb_search_successful and not parsed_sources_from_agent:
                final_sources = ["Knowledge Base Search (Incomplete)"] # Be more specific if search happened
        else: # Completed successfully and not general knowledge
            response_type = "agent"
            confidence = 0.80 # Higher confidence for clean, grounded completion
            final_sources = parsed_sources_from_agent or ["Knowledge Base Search"] # Assume KB if not parsed


        # Clean source citations from the main response text (only if we successfully parsed sources)
        cleaned_response_text = final_response_text
        if parsed_sources_from_agent: # Only clean if we have the sources separately
             # Try removing lines starting with Source(s):
             lines = final_response_text.split('\n')
             cleaned_lines = [line for line in lines if not re.match(r"^\s*Source[s]?:", line, re.IGNORECASE)]
             cleaned_response_text = "\n".join(cleaned_lines).strip()
             # Remove potential empty lines left after cleaning
             cleaned_response_text = re.sub(r'\n\s*\n', '\n\n', cleaned_response_text).strip()


        return {
            "response": cleaned_response_text,
            "type": response_type,
            "confidence": confidence,
            "sources": final_sources # Use the determined list
        }
