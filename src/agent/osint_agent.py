import logging
import json
import re # Import re for parsing
from typing import Dict, List, Any, Optional

from langchain.schema import Document # Assuming this might be used for context typing

# Use relative imports if base_agent and tools are in the same directory level
from .base_agent import BaseAgent
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

class OsintAnalysisAgent(BaseAgent):
    """Agent specialized for OSINT analysis tasks."""

    def __init__(self, llm_service, knowledge_base, tool_registry: ToolRegistry):
        """
        Initialize the OSINT analysis agent.

        Args:
            llm_service: The LLM service used for reasoning and generation
            knowledge_base: KnowledgeBase instance (likely KnowledgeBaseManager)
            tool_registry: ToolRegistry instance for tool access
        """
        # Initialize BaseAgent with llm_service, tools list will be populated later
        super().__init__(llm_service)
        self.knowledge_base = knowledge_base # Should be the KnowledgeBaseManager instance
        self.tool_registry = tool_registry
        self._register_agent_tools() # Renamed for clarity

    def _register_agent_tools(self):
        """Register the tools specifically for this agent instance."""
        # Clear existing tools from base class if any were inherited unexpectedly
        self.tools = []
        # Get tools from the registry provided during initialization
        for name in self.tool_registry.tools:
             tool_details = self.tool_registry.get_tool(name)
             self.add_tool({
                 "name": tool_details["name"],
                 "description": tool_details["description"]
                 # Function is accessed via tool_registry.execute_tool
             })
        logger.info(f"OSINT Agent initialized with {len(self.tools)} tools.")

    def _enhanced_react_prompt(self, query: str, context: Optional[List[Document]] = None) -> str:
        """
        Create an enhanced ReAct-style prompt for OSINT analysis.
        Includes explicit instruction to use "Final Answer:".
        """
        context_str = ""
        if context:
            context_str = "## Intelligence Context Information:\n"
            for i, doc in enumerate(context):
                doc_metadata = getattr(doc, 'metadata', {})
                doc_page_content = getattr(doc, 'page_content', '')
                source = doc_metadata.get('source', 'Unknown Source')
                doc_type = doc_metadata.get('doc_type', 'Unknown Type')
                context_str += f"Document {i+1} from {source} ({doc_type}):\n{doc_page_content}\n\n"

        tools_str = self._format_tools_for_prompt()

        prompt = f"""
You are an expert OSINT analyst specializing in cybersecurity intelligence.
Your primary goal is to answer security-related questions accurately and comprehensively based on information retrieved from the knowledge base.

# Available Tools
You have access to the following tools:
{tools_str}

# IMPORTANT Instructions for Analysis Process:
1.  **Prioritize Knowledge Base:** ALWAYS start by using the `search_kb` tool to find relevant information for the user's query in the knowledge base, unless the query *only* asks to extract entities from a specific text already provided or is a trivial greeting.
2.  **Think Step-by-Step:** Clearly outline your reasoning (Thought:) before deciding on an action.
3.  **Use Tools Correctly:**
    *   To use `search_kb`, provide a concise and relevant search query as the Action Input.
    *   To use `extract_entities`, the Action Input MUST be the specific text block you want to analyze.
    *   To use `analyze_relationships` or `create_timeline`, the Action Input MUST be the structured JSON data (entities list or events list) derived from previous steps or context. These tools DO NOT search the knowledge base themselves.
4.  **Observe Results:** After using a tool, state the Observation clearly.
5.  **Synthesize and Answer:** Based on your thoughts and the observations from tool use (especially `search_kb`), formulate a comprehensive answer to the original query.
6.  **Use "Final Answer:":** When you have gathered enough information and synthesized the final response, present it clearly using the prefix "Final Answer:". Stop the process after providing the Final Answer.
7.  **Cite Sources:** If your answer uses information from the knowledge base (retrieved via `search_kb`), cite the relevant document source(s) within your Final Answer.
8.  **Acknowledge Limitations:** If the knowledge base search does not yield relevant information, state that clearly in your Final Answer. Do not invent information.
9.  **Format:** Strictly follow the Thought, Action, Action Input, Observation format UNTIL you are ready to provide the Final Answer. Start the final answer ONLY with "Final Answer:".

{context_str}

# Intelligence Query
{query}

Let's analyze this systematically, starting with a thought about searching the knowledge base:
Thought: """
        return prompt

    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse the LLM's response. Looks specifically for 'Final Answer:'.
        Extracts the last action block if no Final Answer is found.
        Corrected variable initialization and logic V3.
        """
        response = response.strip()
        final_response_text = "" 
        thoughts = []
        actions = []

        # Check for the explicit "Final Answer:" signal first
        # Use re.DOTALL to make '.' match newlines, re.IGNORECASE for flexibility
        final_answer_match = re.search(r"(?:^|\n)Final Answer:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        if final_answer_match:
            final_response_text = final_answer_match.group(1).strip()
            # Extract thoughts that appeared *before* the final answer signal
            text_before_final_answer = response[:final_answer_match.start()]
            thoughts = [t.strip() for t in re.findall(r"(?:^|\n)Thought:\s*(.*)", text_before_final_answer, re.DOTALL)]
            logger.debug("Found 'Final Answer:' block.")
            # If Final Answer is found, we don't need to look for actions in this response
            actions = []

        else:
            # No "Final Answer:", parse for thoughts and the last action
            thoughts = [t.strip() for t in re.findall(r"(?:^|\n)Thought:\s*(.*)", response, re.DOTALL)]

            # Regex patterns: Action is usually a single word, Input can be multi-line
            action_pattern = r"(?:^|\n)Action:\s*(\S+)"
            action_input_pattern = r"(?:^|\n)Action Input:\s*(.*)"

            action_match = None
            action_input_match = None
            last_action_start = -1
            last_structured_block_end = 0

            # Find the last occurrence of "Action:"
            action_matches = list(re.finditer(action_pattern, response))
            if action_matches:
                action_match = action_matches[-1]
                last_action_start = action_match.start()

                # Look for "Action Input:" *only after* the last "Action:"
                action_input_matches = list(re.finditer(action_input_pattern, response[last_action_start:], re.DOTALL))
                if action_input_matches:
                    action_input_match = action_input_matches[0] # Find the first one after the last action
                    last_structured_block_end = last_action_start + action_input_match.end()
                else:
                     # If Action exists but no Input, mark end after Action
                     last_structured_block_end = action_match.end()


            if action_match and action_input_match:
                tool_name = action_match.group(1).strip()
                tool_input = action_input_match.group(1).strip()

                # Find the last thought occurring *before* this action block
                last_thought_before_action = "No thought recorded"
                thought_matches = list(re.finditer(r"(?:^|\n)Thought:\s*(.*)", response[:last_action_start], re.DOTALL))
                if thought_matches:
                    last_thought_before_action = thought_matches[-1].group(1).strip()

                actions.append({ # Only append the last action found
                    "thought": last_thought_before_action,
                    "action": tool_name,
                    "input": tool_input
                })
            elif action_match:
                 # Only Action found, no input following it
                 logger.warning(f"Parser found Action '{action_match.group(1).strip()}' but no subsequent Action Input.")
                 # We record no valid action block in this case
                 actions = []
            # If no action found, actions list remains empty

            # Check for potential final response text if NO explicit tag AND NO valid action block found
            if not final_response_text and not actions:
                # Consider text after the last thought (if any) as potential response
                text_after_last_thought = response
                if thoughts:
                     last_thought_match = list(re.finditer(r"(?:^|\n)Thought:\s*(.*)", response, re.DOTALL))
                     if last_thought_match:
                          text_after_last_thought = response[last_thought_match[-1].end():].strip()

                if text_after_last_thought and not text_after_last_thought.startswith("Thought:"):
                    final_response_text = text_after_last_thought
                    logger.debug("No 'Final Answer:' tag or valid action found, treating trailing text as final response.")
                elif not thoughts: # No thoughts, no actions, no Final Answer tag
                    final_response_text = response # Treat the whole response as final
                    logger.debug("No structured elements found, treating whole response as final.")


        return {
            "thoughts": thoughts, # All thoughts captured in this turn's response
            "actions": actions,   # The *last* valid action block found (if any, and if no Final Answer)
            "final_response": final_response_text # Text after "Final Answer:", or inferred trailing text, or empty
        }


    def execute(self, query: str, context: Optional[List[Document]] = None) -> Dict:
        """
        Execute the OSINT analysis agent on a query using a ReAct loop.
        Uses 'Final Answer:' signal for termination and refined observation handling.
        """
        logger.info(f"Executing OSINT analysis agent (ReAct) on query: {query}")

        initial_prompt = self._enhanced_react_prompt(query, context)
        max_iterations = 5
        current_interaction_history = initial_prompt # Accumulates full interaction

        all_thoughts = [] # Store all thoughts across iterations
        all_actions = [] # Store all actions taken across iterations
        last_observation = None # Store observation from the previous turn
        action_executed_in_last_turn = False # Flag

        for i in range(max_iterations):
            logger.info(f"ReAct Iteration {i+1}/{max_iterations}")

            # --- Construct the prompt for this turn ---
            prompt_for_llm = current_interaction_history
            # Add explicit guidance if we just received an observation
            if action_executed_in_last_turn:
                # Append the observation itself first (already done at end of previous loop)
                # Now add guidance
                prompt_for_llm += "\nThought: Analyze the Observation above. If it provides enough information to answer the original query comprehensively, formulate the 'Final Answer:'. Otherwise, determine the next Thought and Action needed to get closer to the answer."
                prompt_for_llm += "\nThought:" # Prompt for the next thought
                action_executed_in_last_turn = False # Reset flag after using it

            # --- Call LLM ---
            llm_response_text = self.llm_service.generate(prompt_for_llm)
            # Append LLM's full response to history *before* parsing it
            current_interaction_history += "\n" + llm_response_text

            # --- Parse LLM's latest response ---
            parsed = self._parse_llm_response(llm_response_text)

            # Store thoughts from this turn
            if parsed["thoughts"]:
                # Add only thoughts specifically from *this* LLM response turn
                # This avoids duplicating thoughts already in the history passed to the parser
                # A bit tricky - let's just log all thoughts found in this parse for now
                all_thoughts.extend(parsed["thoughts"]) # May contain duplicates across turns

            # --- Decision Logic ---
            # Check if the parser found an explicit "Final Answer:"
            if parsed["final_response"]:
                logger.info("Agent produced 'Final Answer:' block. Terminating loop.")
                # Attempt to parse sources from the final answer block
                parsed_sources = []
                source_matches = re.findall(r"Source[s]?:\s*([^\n]+)", parsed["final_response"], re.IGNORECASE)
                for match in source_matches:
                    # Split potential comma-separated lists, strip quotes/whitespace
                    parsed_sources.extend([s.strip().strip('"') for s in match.split(',') if s.strip()])

                final_result_dict = { # Create the dictionary explicitly
                    "query": query,
                    "conversation_history": current_interaction_history,
                    "thoughts": all_thoughts,
                    "actions": all_actions,  # Make sure it's using all_actions
                    "response": parsed["final_response"],
                    "status": "completed",
                    "parsed_sources": list(set(parsed_sources))
                }
                # --->>> Add logging here <<<---
                logger.debug(f"Agent returning completed result: {final_result_dict}")
                return final_result_dict
            # If no Final Answer, check if there's an Action to perform
            elif parsed["actions"]:
                action_to_execute = parsed["actions"][0] # Parser gives only the last action
                tool_name = action_to_execute["action"]
                tool_input = action_to_execute["input"]
                all_actions.append(action_to_execute) # Log the action being taken

                logger.info(f"Agent decided to use tool: {tool_name} with input: {str(tool_input)[:100]}...") # Log input safely
                try:
                    tool_result = self.tool_registry.execute_tool(tool_name, tool_input)
                    tool_result_str = str(tool_result)
                    # Limit observation size
                    if len(tool_result_str) > 1500:
                        tool_result_str = tool_result_str[:1500] + "...\n[Result truncated]"
                    last_observation = tool_result_str
                    action_executed_in_last_turn = True

                except KeyError:
                    logger.warning(f"Agent tried to use non-existent tool: {tool_name}")
                    last_observation = f"Error: Tool '{tool_name}' not found. Please use one of the available tools."
                    action_executed_in_last_turn = True # Still treat as a turn completion
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    last_observation = f"Error executing tool {tool_name}: {str(e)}"
                    action_executed_in_last_turn = True

                # Append observation for the next LLM call's context
                current_interaction_history += f"\nObservation: {last_observation}"
                # The next loop iteration will add the specific "Analyze Observation" thought prompt

            # No Final Answer and no Action
            else:
                logger.warning("LLM did not specify a valid Action or Final Answer in this turn. Continuing loop.")
                last_observation = None # Reset observation status
                action_executed_in_last_turn = False
                # Append Thought prompt to encourage LLM to continue reasoning
                current_interaction_history += "\nThought:"


        # Max iterations reached
        logger.warning(f"Agent reached max iterations ({max_iterations}). Returning final response attempt.")
        # Re-parse the very last output to get the final thought/response piece
        last_parsed = self._parse_llm_response(llm_response_text)
        final_response = last_parsed.get("final_response", "").strip()

        if not final_response and all_thoughts:
             # If no final block, use the very last thought recorded as the response
             final_response = "Analysis based on last thought: " + all_thoughts[-1]
        elif not final_response:
             final_response = "Agent reached maximum analysis steps without providing a conclusive final answer."


        return {
            "query": query,
            "conversation_history": current_interaction_history,
            "thoughts": all_thoughts,
            "actions": all_actions,
            "response": final_response,
            "status": "max_iterations_reached",
            "parsed_sources": [] # No specific sources parsed if max iterations hit
        }