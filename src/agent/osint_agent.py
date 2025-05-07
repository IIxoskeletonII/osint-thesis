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
        actions = [] 

        final_answer_match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        if final_answer_match:
            final_response_text = final_answer_match.group(1).strip()
            text_before_final_answer = response[:final_answer_match.start()]
            last_thought_match = list(re.finditer(r"Thought:\s*(.*?)(?=\nAction:|\nObservation:|\nFinal Answer:|$)", text_before_final_answer, re.DOTALL | re.IGNORECASE))
            if last_thought_match:
                thoughts.append(last_thought_match[-1].group(1).strip())
            logger.debug("Found 'Final Answer:' block.")
        else:
            last_block_match = None
            for match in re.finditer(
                r"Thought:\s*(.*?)\nAction:\s*(\S+)\s*\nAction Input:\s*(.*?)(?=(\nThought:|\nObservation:|\nFinal Answer:|$))",
                response,
                re.DOTALL | re.IGNORECASE
            ):
                last_block_match = match
            
            if last_block_match:
                thought_text = last_block_match.group(1).strip()
                tool_name = last_block_match.group(2).strip()
                tool_input = last_block_match.group(3).strip()
                
                thoughts.append(thought_text)
                actions.append({
                    "thought": thought_text,
                    "action": tool_name,
                    "input": tool_input
                })
                logger.debug(f"Parsed Action: {tool_name} with Input: {tool_input[:100]}...")
            else:
                last_thought_match = list(re.finditer(r"Thought:\s*(.*?)(?=\nAction:|\nObservation:|\nFinal Answer:|$)", response, re.DOTALL | re.IGNORECASE))
                if last_thought_match:
                    thoughts.append(last_thought_match[-1].group(1).strip())
                logger.debug("No parsable action block found in this turn, or only a thought was generated.")

        return {
            "thoughts": thoughts,
            "actions": actions, 
            "final_response": final_response_text
        }

    def execute(self, query: str, context: Optional[List[Document]] = None) -> Dict[str, Any]:
        logger.info(f"Executing OSINT analysis agent (ReAct) on query: {query}")

        max_iterations = 5
        
        history_for_llm = f"LATEST USER QUERY: {query}\n"
        if context:
            context_str = "## Initial Context Provided:\n"
            for i, doc_ctx in enumerate(context): 
                doc_metadata = getattr(doc_ctx, 'metadata', {})
                doc_page_content = getattr(doc_ctx, 'page_content', '')
                source_name_ctx = doc_metadata.get('source', 'Unknown Source')
                context_str += f"Document {i+1} from {source_name_ctx}:\n{doc_page_content}\n\n"
            history_for_llm = context_str + history_for_llm
            
        full_conversation_log = [history_for_llm] 
        all_actions_taken_structured: List[Dict[str, str]] = []
        cited_kb_documents: Dict[str, Dict[str, Any]] = {} 
        
        force_initial_search = True
        if query.strip().lower() in ["hi", "hello", "hey", "/help", "/clear"] or query.strip().startswith("/"):
            force_initial_search = False

        for i in range(max_iterations):
            logger.info(f"ReAct Iteration {i+1}/{max_iterations}")
            current_prompt_for_llm = self._enhanced_react_prompt(query, history_for_llm)
            action_detail_for_this_turn: Optional[Dict[str,str]] = None 

            if i == 0 and force_initial_search:
                logger.info("Forcing initial knowledge base search for this query type.")
                thought_text = f"The user is asking about '{query}'. I must consult the knowledge base first for information related to this cybersecurity query."
                tool_name = "search_kb"
                tool_input = query 
                history_for_llm += f"Thought: {thought_text}\n"
                full_conversation_log.append(f"LLM Response {i+1} (Forced Action):\nThought: {thought_text}\nAction: {tool_name}\nAction Input: {tool_input}")
                action_detail_for_this_turn = {"thought": thought_text, "action": tool_name, "input": tool_input}
            else:
                llm_response_text = self.llm_service.generate(current_prompt_for_llm)
                full_conversation_log.append(f"LLM Response {i+1}:\n{llm_response_text}")
                parsed = self._parse_llm_response(llm_response_text)
                
                current_turn_thoughts = parsed.get("thoughts", [])
                for t_text in current_turn_thoughts:
                    history_for_llm += f"Thought: {t_text}\n"

                if parsed["final_response"]:
                    logger.info("Agent produced 'Final Answer:' block. Terminating loop.")
                    final_response_text = parsed["final_response"]
                    
                    logger.debug(f"Exiting with Final Answer. Content of cited_kb_documents before returning: {json.dumps(list(cited_kb_documents.values()), indent=2)}")
                    
                    collated_thoughts = [act_item.get("thought", "") for act_item in all_actions_taken_structured if act_item.get("thought")] + current_turn_thoughts

                    return {
                        "query": query,
                        "conversation_history": "\n".join(full_conversation_log),
                        "thoughts": collated_thoughts,
                        "actions": all_actions_taken_structured,
                        "response": final_response_text,
                        "status": "completed",
                        "parsed_sources": list(cited_kb_documents.values()) 
                    }

                action_block = parsed.get("actions")
                if action_block: 
                    action_detail_for_this_turn = action_block[0]
                else: 
                    logger.warning("LLM did not specify a valid Action in this turn. Will re-prompt.")
                    if i == max_iterations - 1: break 
                    history_for_llm += "Thought:" 
                    continue 
            
            if action_detail_for_this_turn:
                tool_name = action_detail_for_this_turn["action"]
                tool_input = action_detail_for_this_turn["input"]
                all_actions_taken_structured.append(action_detail_for_this_turn) 
                history_for_llm += f"Action: {tool_name}\nAction Input: {tool_input}\n"
                logger.info(f"Agent decided to use tool: {tool_name} with input: {str(tool_input)[:100]}...")

                try:
                    tool_result_obj = self.tool_registry.execute_tool(tool_name, tool_input) 
                    
                    if tool_name == "search_kb":
                        logger.debug(f"Tool 'search_kb' returned tool_result_obj keys: {list(tool_result_obj.keys()) if isinstance(tool_result_obj, dict) else 'Not a dict'}")
                        if isinstance(tool_result_obj, dict) and "structured_results" in tool_result_obj:
                            logger.debug(f"First item in structured_results (if any): {json.dumps(tool_result_obj['structured_results'][0] if tool_result_obj['structured_results'] else None, indent=2)}")
                            logger.debug(f"Number of structured_results: {len(tool_result_obj['structured_results'])}")
                    
                    if tool_name == "search_kb" and isinstance(tool_result_obj, dict) and "observation_text" in tool_result_obj:
                        observation_text_for_llm = tool_result_obj["observation_text"]
                        if "structured_results" in tool_result_obj and tool_result_obj["structured_results"]: # Ensure it's not empty
                            for doc_detail in tool_result_obj["structured_results"]:
                                chunk_id_key = doc_detail.get("id", doc_detail.get("chunk_id")) 
                                if chunk_id_key:
                                     cited_kb_documents[chunk_id_key] = doc_detail
                                     logger.debug(f"Added/Updated doc_detail for chunk_id {chunk_id_key} in cited_kb_documents.") # DEBUG
                        else:
                            logger.debug("Tool 'search_kb' returned no 'structured_results' or it was empty.")

                    else: 
                        observation_text_for_llm = str(tool_result_obj)
                    
                    if len(observation_text_for_llm) > 2000:
                        observation_text_for_llm = observation_text_for_llm[:2000] + "...\n[Result truncated due to length]"
                    history_for_llm += f"Observation: {observation_text_for_llm}\n"
                except KeyError:
                    logger.warning(f"Agent tried to use non-existent tool: {tool_name}")
                    history_for_llm += f"Observation: Error: Tool '{tool_name}' not found. Please use one of the available tools.\n"
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    history_for_llm += f"Observation: Error executing tool {tool_name}: {str(e)}\n"
            else:
                if i < max_iterations - 1:
                    logger.debug("No action to execute in this iteration, continuing to next thought.")

        logger.warning(f"Agent reached max iterations ({max_iterations}) or loop broken without Final Answer. Returning final summary attempt.")
        logger.debug(f"Exiting due to max_iterations. Content of cited_kb_documents: {json.dumps(list(cited_kb_documents.values()), indent=2)}")
        final_summary_prompt = history_for_llm + "\nThought: I have processed the available information and reached the iteration limit. I need to synthesize a final answer based on the gathered thoughts and observations for the LATEST USER QUERY.\nFinal Answer:"
        final_response_text = self.llm_service.generate(final_summary_prompt)
        
        final_answer_match_summary = re.search(r"Final Answer:\s*(.*)", final_response_text, re.DOTALL | re.IGNORECASE)
        if final_answer_match_summary:
            final_response_text = final_answer_match_summary.group(1).strip()

        return {
            "query": query,
            "conversation_history": "\n".join(full_conversation_log),
            "thoughts": [act_item.get("thought", "") for act_item in all_actions_taken_structured if act_item.get("thought")],
            "actions": all_actions_taken_structured,
            "response": final_response_text or "Agent reached maximum analysis steps without providing a conclusive final answer.",
            "status": "max_iterations_reached",
            "parsed_sources": list(cited_kb_documents.values()) 
        }