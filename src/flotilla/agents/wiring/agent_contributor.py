from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.agents.wiring.agent_context import AgentContext
from flotilla.config.config_utils import ConfigUtils
from flotilla.llm.llm_factory import LLMFactory
from flotilla.utils.logger import get_logger
from flotilla.core.errors import FlotillaConfigurationError


logger = get_logger(__name__)

class AgentContributor:

    name = "agent-contributor"
    priority = 50   # must run after LLM builders are registered

    def contribute(self, container: FlotillaContainer, context: AgentContext) -> None:
        cfg = container.config_dict
        agents_cfg = cfg.get("agents")

        if agents_cfg is None:
            logger.warn("Configuration for Agents did not exist")
            return
        
        checkpointer = container.get("checkpointer")
        if not checkpointer:
            raise FlotillaConfigurationError("Required component checkpointer does not exist on FlotillaContainer")

        for agent_name, agent_cfg in agents_cfg.items():
            logger.info(f"Register Agent {agent_name} on the FlotillaContainer after loading its LLM")    

            # for each agent resolve its LLM if it exists, getting the LLM Provider referenced by the agent config and the agent's llm overrides
            base_path = f"llm." + agent_cfg.get("llm", {}).get("provider")
            override_path =  f"agents." + agent_name + ".llm"
            llm_cfg = ConfigUtils.resolve_flattened_config(config=cfg, base_path=base_path, override_path=override_path)
            llm = LLMFactory.create(container=container, llm_config=llm_cfg)
            logger.debug(f"Found llm {llm} for agent {agent_name}")
            
            # then register it on the container as singleton
            container.wire_from_config(section="agents", name=agent_name, config_path=agent_name, llm=llm, checkpointer=checkpointer)

            # add the agent to the list of names to retrieved by the builder
            context.agent_names.append(agent_name)
        

    
    def validate(self, container:FlotillaContainer, context:AgentContext):
        pass