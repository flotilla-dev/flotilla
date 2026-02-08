from flotilla.agents.agent_selector import AgentSelector
from flotilla.core.agent_input import AgentInput
from typing import Dict
from flotilla.agents.base_business_agent import BaseBusinessAgent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from flotilla.utils.logger import get_logger
import json

logger = get_logger(__name__)

class LLMAgentSelector(AgentSelector):


    def select_agent(self, agent_input:AgentInput, agents:Dict[str, BaseBusinessAgent]):
        pass

    """
    AgentSelector that uses an LLM to select from the provided Agents.
    """
'''
    def __init__(self, config: LLMAgentSelectorConfig):
        if not isinstance(config, LLMAgentSelectorConfig):
            raise TypeError(f"Unsupported config object {type(config)}")

        super().__init__("LLMAgentSelector", config)
        self.llm = LLMFactory.get_llm(config.llm_config)
        self.min_confidence = config.min_confidence

    def _extract_llm_content(self, response):
        """Safely extract message content regardless of LLM invoke format."""
        if isinstance(response, AIMessage):
            return response.content
        if isinstance(response, dict) and "messages" in response:
            msgs = response["messages"]
            return msgs[-1].content
        raise ValueError("Unexpected LLM response structure")

    def select_agent(self, query: str, agents: Dict[str, BaseBusinessAgent]):
        """
        Uses the LLM to intelligently select the best agent.
        Returns: BaseBusinessAgent or None
        """
        agent_descriptions = []
        for agent_id, agent in agents.items():
            caps = agent.get_capabilities()
            formatted_caps = "\n".join(
                [f"  - {cap.name}: {cap.description}" for cap in caps]
            )
            agent_descriptions.append(
                f"Agent ID: {agent_id}\n"
                f"Name: {agent.agent_name}\n"
                f"Capabilities:\n{formatted_caps}"
            )

        system_prompt = """
You are an intelligent agent selector inside a multi-agent system.

Your task:
- Read the user's query.
- Read the available agents and their capabilities.
- Determine which agent is the best match.
- Assign a confidence score (0.0-1.0).

Return ONLY JSON in this format:
{
  "agent_id": "<agent_id or null>",
  "confidence": <float>
}
"""

        user_prompt = f"""
User Query: {query}

Available Agents:
{chr(10).join(agent_descriptions)}

Return ONLY JSON:
{{
  "agent_id": "<agent_id>",
  "confidence": <float>
}}
"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            raw = self._extract_llm_content(response)
            result = json.loads(raw)

            agent_id = result.get("agent_id")
            confidence = float(result.get("confidence", 0.0))

            if confidence < self.min_confidence:
                logger.info(
                    f"Agent rejected due to low confidence ({confidence} < {self.min_confidence})"
                )
                return None

            if agent_id in agents:
                return agents[agent_id]

            logger.warning(f"LLM returned unknown agent ID: {agent_id}")
            return None

        except Exception as e:
            logger.error(f"LLM agent selection failed: {e}")
            return None
'''