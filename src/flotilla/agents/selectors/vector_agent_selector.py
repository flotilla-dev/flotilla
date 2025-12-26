from flotilla.agents.agent_selector import AgentSelector
from flotilla.agents.base_business_agent import BaseBusinessAgent
from flotilla.config_models import VectorAgentSelectorConfig
from flotilla.utils.logger import get_logger
from typing import Optional, List, Dict
import numpy as np
from numpy import ndarray

logger = get_logger(__name__)

class VectorAgentSelector(AgentSelector):

    def select_agent(self, query, agents):
        pass
'''        

    def __init__(self, config : VectorAgentSelectorConfig):
        if not isinstance(config, VectorAgentSelectorConfig):
            raise TypeError("VectorAgentSelector requires an instance of VectorAgentSelectorConfig")
        super().__init__("VectorAgentSelector", config)
        self.embeddings = config.embedding_model

    def select_agent(self, query: str, agents: Dict[str, BaseBusinessAgent]) -> Optional[BaseBusinessAgent]:
        """Select the best agent using vector similarity"""
        # Vectorize the query
        query_vector = self._vectorize_text(query)  # Fixed typo

        # Define high score & high score agent
        selected_score = -1.0
        selected_agent = None

        for agent in agents.values():
            # Build combined text and vectorize - PASS AS LIST
            agent_text = self._build_combined_agent_text(agent)
            agent_vectors = self._vectorize_texts([agent_text])  # FIX: Wrap in list!
            
            # Calculate similarities (agent_vectors is 2D, query_vector is 1D)
            similarities = np.dot(agent_vectors, query_vector)  # shape: (1,)
            max_score = similarities[0] if similarities.size > 0 else -1.0  # Extract scalar
            
            logger.debug(f"Agent '{agent.agent_name}' similarity: {max_score:.4f}")

            if max_score > selected_score and max_score >= self.config.min_confidence:
                selected_agent = agent
                selected_score = max_score
                logger.info(f"New best agent: '{agent.agent_name}' with score {max_score:.4f}")
        
        if selected_agent:
            logger.info(f"Selected agent: '{selected_agent.agent_name}' (score: {selected_score:.4f})")
        else:
            logger.warning(f"No agent met min_confidence threshold of {self.config.min_confidence}")
        
        return selected_agent

    def _build_combined_agent_text(self, agent: BaseBusinessAgent) -> str:
        """Build text directly from agent capabilities"""
        capabilities = agent.get_capabilities()  # Returns List[AgentCapability]
        
        parts = [f"Agent: {agent.agent_name}"]
        
        for cap in capabilities:
            parts.append(f"Capability: {cap.name}")
            parts.append(f"Description: {cap.description}")
            
            if cap.keywords:
                parts.append(f"Keywords: {', '.join(cap.keywords)}")
            
            if cap.examples:
                parts.append(f"Examples: {' | '.join(cap.examples)}")
        
        return "\n".join(parts)

    def _vectorize_text(self, text: str) -> ndarray:  # Fixed typo
        """
        Uses the Embeddings model passed as part of the config to vectorize the provided 
        single string of text. It is then normalized into a Numpy NDArray to make 
        dot matrix mathematic comparison easy

        Args:
            text - The single string of text to convert to a vector
        
        Returns:
            A ndarray vectorized for the provided text
        """
        logger.debug(f"Vectorizing text: '{text[:100]}...'")  # Truncate for logging
        query_embedding = self.embeddings.embed_query(text=text)
        query_vec = np.array(query_embedding)
        normalized = query_vec / np.linalg.norm(query_vec)
        logger.debug(f"Created normalized vector of shape {normalized.shape}")
        return normalized
    
    def _vectorize_texts(self, texts: List[str]) -> ndarray:
        """
        Embed a list of texts and normalize them to unit vectors.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Normalized numpy array of shape (num_texts, embedding_dim)
            Ready for np.dot() operations
        """
        logger.debug(f"Vectorizing {len(texts)} texts")

        # Handle empty list case
        if not texts:
            # Return empty array with correct shape (0 rows, but preserve embedding dimension)
            # Note: embedding dimension is unknown without calling the model
            return np.empty((0, 0))

        # Get embeddings for all texts (batch operation)
        embeddings_list = self.embeddings.embed_documents(texts)  # list[list[float]]
        
        # Convert to numpy array (each row is one text's embedding)
        embeddings_matrix = np.array(embeddings_list)  # shape: (num_texts, embedding_dim)
        
        # Normalize each row to unit length
        norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)  # shape: (num_texts, 1)
        normalized_matrix = embeddings_matrix / norms
        
        logger.debug(f"Created normalized matrix of shape {normalized_matrix.shape}")
        return normalized_matrix
'''