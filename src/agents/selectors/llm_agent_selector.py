def _llm_select_agent(self, query: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Use LLM to intelligently select the best agent
        
        Returns:
            Agent ID or None
        """
        '''
        # Build agent descriptions
        agent_descriptions = []
        for agent_id, agent in self.agents.items():
            capabilities = "\n".join([
                f"  - {cap.name}: {cap.description}"
                for cap in agent.get_capabilities()
            ])
            agent_descriptions.append(
                f"Agent ID: {agent_id}\n"
                f"Name: {agent.agent_name}\n"
                f"Capabilities:\n{capabilities}"
            )
        
        system_prompt = """You are an intelligent query router. Based on the user query and available agents, 
        select the MOST APPROPRIATE agent to handle the request. Consider the query intent, keywords, and 
        which agent's capabilities best match the user's needs.
        
        Respond with ONLY the agent ID, nothing else."""
        
        user_prompt = f"""
        User Query: {query}
        
        {f"Context: {context}" if context else ""}
        
        Available Agents:
        {chr(10).join(agent_descriptions)}
        
        Select the best agent ID:
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            selected_id = response.content.strip()
            
            # Validate the response is a known agent ID
            if selected_id in self.agents:
                return selected_id
            else:
                logger.warning(f"LLM returned unknown agent ID: {selected_id}")
                return None
                
        except Exception as e:
            logger.error(f"LLM agent selection failed: {e}")
            return None
        '''