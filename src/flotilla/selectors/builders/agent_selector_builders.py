
from flotilla.selectors.keyword_agent_selector import KeywordAgentSelector

def keyword_agent_selector_builder(min_confidence:float) -> KeywordAgentSelector:
    return KeywordAgentSelector(min_confidence=min_confidence)