from langgraph.checkpoint.memory import InMemorySaver

def memory_checkpointer_buidler() -> InMemorySaver:
    return InMemorySaver()