import logging
import json
import re
from typing import Dict, List, Any, Optional

from langchain.schema import Document 
from .base_agent import BaseAgent
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

class OsintAnalysisAgent(BaseAgent):
    def __init__(self, llm_service, knowledge_base, tool_registry: ToolRegistry):
        super().__init__(llm_service)
        self.knowledge_base = knowledge_base
        self.tool_registry = tool_registry
        self._register_agent_tools()
        logger.info(f"OSINT Agent initialized with {len(self.tools)} tools.")

    def _register_agent_tools(self):
        self.tools = []
        for name in self.tool_registry.tools:
            tool_details = self.tool_registry.get_tool(name)
            self.add_tool({
                "name": tool_details["name"],
                "description": tool_details["description"]
            })

    def _enhanced_react_prompt(self, query: str, history_for_llm: str) -> str:
            """
            Create an enhanced ReAct-style prompt for OSINT analysis.
            Now takes a formatted history string.
            """
            tools_str = self._format_tools_for_prompt()

            # The core instruction block
            instruction_block = f"""
    You are an expert OSINT analyst specializing in cybersecurity intelligence.
    Your primary goal is to answer the LATEST USER QUERY accurately and comprehensively, prioritizing information from the specialized knowledge base.

    # Available Tools
    You have access to the following tools:
    {tools_str}

    # IMPORTANT Instructions for Analysis Process:
    1.  **Understand the Goal:** Focus on answering the LATEST USER QUERY using the knowledge base.
    2.  **Think Step-by-Step:** Clearly outline your reasoning (Thought:) before deciding on an action.
    3.  **ALWAYS Use `search_kb` First for Information Retrieval:** For any query that asks for information, definitions, explanations, analysis, or comparisons related to cybersecurity (like vulnerabilities, malware, threat actors, attack techniques, security concepts), your VERY FIRST action MUST BE `search_kb` to consult the specialized knowledge base. Only after reviewing the Observation from `search_kb` should you decide if more searches are needed or if you can formulate a Final Answer. Do not rely solely on general knowledge for cybersecurity topics if the KB might contain relevant details. Exception: If the query is a simple greeting or a direct command like "/clear" or "/help", you don't need to search the KB.
    4.  **Tool Usage Format:**
        Thought: Your reasoning for the action.
        Action: tool_name_exactly_as_listed
        Action Input: The specific input for the tool. For `search_kb`, this MUST be a concise search query string. For `extract_entities`, it's the text block. For others, it's specific JSON.
    5.  **Review Observation:** After an action, you will receive an "Observation:". Analyze it carefully.
    6.  **Iterate if Necessary:** If the observation is insufficient or doesn't directly answer the LATEST USER QUERY, formulate a NEW thought and decide on the NEXT action (which might be another `search_kb` with a refined query, or a different tool if appropriate). Your subsequent `search_kb` Action Input should be a REFINED query based on new insights, not the entire previous observation.
    7.  **Synthesize and Answer:** When you have gathered enough information from the knowledge base (and potentially other tools), synthesize the final response.
    8.  **Use "Final Answer:":** Prefix your complete, final answer with "Final Answer:". Stop after this.
    9.  **Cite Sources:** If your Final Answer uses information from `search_kb` Observations, cite the document titles or IDs (and ideally File Paths if available in the observation) mentioned in those observations.
    10. **Acknowledge Limitations:** If, after searching the knowledge base, the information isn't found or is insufficient, state that clearly in your Final Answer.

    # Conversation History & Current Task:
    {history_for_llm}
    Thought:"""
            return instruction_block

    def _parse_llm_response(self, response: str) -> Dict:
        response = response.strip()
        final_response_text = ""
        thoughts = []
        actions = [] # Will now only store the single, last valid action from a response turn

        final_answer_match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        if final_answer_match:
            final_response_text = final_answer_match.group(1).strip()
            text_before_final_answer = response[:final_answer_match.start()]
            # Capture the last thought before the final answer
            last_thought_match = list(re.finditer(r"Thought:\s*(.*?)(?=\nAction:|\nObservation:|\nFinal Answer:|$)", text_before_final_answer, re.DOTALL | re.IGNORECASE))
            if last_thought_match:
                thoughts.append(last_thought_match[-1].group(1).strip())
            logger.debug("Found 'Final Answer:' block.")
        else:
            # Try to parse the last thought-action block
            # Regex to find the last "Thought: ... Action: ... Action Input: ..." sequence
            # This regex tries to capture the last full T-A-AI block.
            last_block_match = None
            for match in re.finditer(r"Thought:\s*(.*?)\nAction:\s*(\S+)\s*\nAction Input:\s*(.*?)(?=\nThought:|\nObservation:|$)", response, re.DOTALL | re.IGNORECASE):
                last_block_match = match
            
            if last_block_match:
                thought_text = last_block_match.group(1).strip()
                tool_name = last_block_match.group(2).strip()
                tool_input = last_block_match.group(3).strip()
                
                thoughts.append(thought_text) # Add the thought for this action
                actions.append({ # Store the single action for this turn
                    "thought": thought_text,
                    "action": tool_name,
                    "input": tool_input
                })
                logger.debug(f"Parsed Action: {tool_name} with Input: {tool_input[:100]}...")
            else:
                # No clear action, could be just a thought, or malformed
                last_thought_match = list(re.finditer(r"Thought:\s*(.*?)(?=\nAction:|\nObservation:|\nFinal Answer:|$)", response, re.DOTALL | re.IGNORECASE))
                if last_thought_match:
                    thoughts.append(last_thought_match[-1].group(1).strip())
                logger.debug("No parsable action block found in this turn, or only a thought was generated.")
                # If no action and no final answer, the agent might be stuck or just thinking.
                # The loop in execute() will handle this by re-prompting.

        return {
            "thoughts": thoughts,
            "actions": actions, 
            "final_response": final_response_text
        }

    def execute(self, query: str, context: Optional[List[Document]] = None) -> Dict[str, Any]:
        logger.info(f"Executing OSINT analysis agent (ReAct) on query: {query}")

        max_iterations = 5
        
        # Initialize history for the LLM. Start with the user query.
        # Context documents can be prepended if necessary.
        history_for_llm = f"LATEST USER QUERY: {query}\n"
        if context:
            context_str = "## Initial Context Provided:\n"
            for i, doc in enumerate(context):
                doc_metadata = getattr(doc, 'metadata', {})
                doc_page_content = getattr(doc, 'page_content', '') # Ensure this exists
                source = doc_metadata.get('source', 'Unknown Source')
                context_str += f"Document {i+1} from {source}:\n{doc_page_content}\n\n"
            history_for_llm = context_str + history_for_llm
            
        # Store overall interaction for debugging or full history
        full_conversation_log = [history_for_llm] 
        
        all_actions_taken_structured = [] # Store structured actions for final result


        # Determine if this query should forcibly start with a KB search
        
        force_initial_search = True
        # Add exceptions for simple greetings or commands if needed here, though the prompt already handles some.
        # For example:
        # if query.strip().lower() in ["hi", "hello", "/help", "/clear"]:
        #     force_initial_search = False

        initial_action_taken_this_turn = False 

        for i in range(max_iterations):
            logger.info(f"ReAct Iteration {i+1}/{max_iterations}")

            current_prompt_for_llm = self._enhanced_react_prompt(query, history_for_llm)
            
            # --- MODIFICATION: Force initial search_kb if applicable ---
            if i == 0 and force_initial_search:
                logger.info("Forcing initial knowledge base search for this query type.")
                # Simulate the LLM deciding to search_kb
                # The thought can be generic or derived from the query
                thought_text = f"The user is asking about '{query}'. I must consult the knowledge base first for information related to this cybersecurity query."
                tool_name = "search_kb"
                # The LLM would ideally generate a good search query, but we can start with the user's query
                tool_input = query # Or a refined version if we add more logic here
                
                history_for_llm += f"Thought: {thought_text}\n"
                history_for_llm += f"Action: {tool_name}\nAction Input: {tool_input}\n"
                full_conversation_log.append(f"LLM Response {i+1} (Forced Action):\nThought: {thought_text}\nAction: {tool_name}\nAction Input: {tool_input}")

                action_detail = {"thought": thought_text, "action": tool_name, "input": tool_input}
                # Fall through to the action execution block
            else:
                # Normal LLM call
                llm_response_text = self.llm_service.generate(current_prompt_for_llm)
                full_conversation_log.append(f"LLM Response {i+1}:\n{llm_response_text}")
                parsed = self._parse_llm_response(llm_response_text)
                
                current_turn_thoughts = parsed.get("thoughts", [])
                for t_text in current_turn_thoughts: # Changed variable name
                    history_for_llm += f"Thought: {t_text}\n" # Append LLM's actual thought

                if parsed["final_response"]:
                    # ... (final answer logic remains the same) ...
                    logger.info("Agent produced 'Final Answer:' block. Terminating loop.")
                    final_response_text = parsed["final_response"]
                    parsed_sources = []
                    source_matches = re.findall(r"Source[s]?:\s*([^\n]+)", final_response_text, re.IGNORECASE)
                    for match in source_matches:
                        parsed_sources.extend([s.strip().strip('"') for s in match.split(',') if s.strip()])
                    return {
                        "query": query,
                        "conversation_history": "\n".join(full_conversation_log),
                        "thoughts": [t for act_item in all_actions_taken_structured for t in [act_item.get("thought", "")] if t] + current_turn_thoughts,
                        "actions": all_actions_taken_structured,
                        "response": final_response_text,
                        "status": "completed",
                        "parsed_sources": list(set(parsed_sources))
                    }

                action_block = parsed.get("actions")
                if not action_block: # If LLM didn't produce an action this turn
                    logger.warning("LLM did not specify a valid Action in this turn. Will re-prompt.")
                    if i == max_iterations - 1: break
                    history_for_llm += "Thought:" # Encourage it to think again
                    continue
                action_detail = action_block[0]
            # --- END MODIFICATION ---

            # --- Common Action Execution Block (for forced or LLM-decided action) ---
            tool_name = action_detail["action"]
            tool_input = action_detail["input"]
            
            all_actions_taken_structured.append(action_detail) 

            # Append action to history_for_llm ONLY IF it wasn't the forced initial action (already added)
            if not (i == 0 and force_initial_search):
                 history_for_llm += f"Action: {tool_name}\nAction Input: {tool_input}\n"
            
            logger.info(f"Agent decided to use tool: {tool_name} with input: {str(tool_input)[:100]}...")

            try:
                tool_result = self.tool_registry.execute_tool(tool_name, tool_input)
                tool_result_str = str(tool_result)
                if len(tool_result_str) > 2000:
                    tool_result_str = tool_result_str[:2000] + "...\n[Result truncated due to length]"
                history_for_llm += f"Observation: {tool_result_str}\n"
            except KeyError:
                logger.warning(f"Agent tried to use non-existent tool: {tool_name}")
                history_for_llm += f"Observation: Error: Tool '{tool_name}' not found. Please use one of the available tools.\n"
            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                history_for_llm += f"Observation: Error executing tool {tool_name}: {str(e)}\n"
            # --- End Common Action Execution Block ---

        # Max iterations reached or broke from loop
        logger.warning(f"Agent reached max iterations ({max_iterations}) or loop broken. Returning final response attempt.")
        final_summary_prompt = history_for_llm + "\nThought: I have processed the available information. I need to synthesize a final answer based on the gathered thoughts and observations for the LATEST USER QUERY.\nFinal Answer:"
        final_response_text = self.llm_service.generate(final_summary_prompt)
        
        final_answer_match_summary = re.search(r"Final Answer:\s*(.*)", final_response_text, re.DOTALL | re.IGNORECASE)
        if final_answer_match_summary:
            final_response_text = final_answer_match_summary.group(1).strip()

        return {
            "query": query,
            "conversation_history": "\n".join(full_conversation_log),
            "thoughts": [t for act_item in all_actions_taken_structured for t in [act_item.get("thought", "")] if t],
            "actions": all_actions_taken_structured,
            "response": final_response_text or "Agent reached maximum analysis steps without providing a conclusive final answer.",
            "status": "max_iterations_reached",
            "parsed_sources": [] 
        }