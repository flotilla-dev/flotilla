from langchain_openai.chat_models.base import ChatOpenAI


def openai_llm_builder(*, api_key:str, model:str, temperature:float = 0.0, max_tokens:int = None,  timeout:float = None, max_retries:int = None, base_url:str = None) -> ChatOpenAI:
    """
    Builder function for creating a Langchain Open AI LLM instance.  The only parameters that are required are api_key and model.  All other parameter either have reasonable 
    defaults or can be handled as None.
    """
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
        base_url=base_url)

