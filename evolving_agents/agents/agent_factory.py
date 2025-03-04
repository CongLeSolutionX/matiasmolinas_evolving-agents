# evolving_agents/agents/agent_factory.py

import logging
from typing import Dict, Any, Optional, List, Union

from evolving_agents.smart_library.smart_library import SmartLibrary
from evolving_agents.core.llm_service import LLMService
from evolving_agents.providers.registry import ProviderRegistry
from evolving_agents.providers.base import FrameworkProvider
from evolving_agents.providers.beeai_provider import BeeAIProvider

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory for creating and executing agents across different frameworks.
    """
    def __init__(
        self, 
        smart_library: SmartLibrary, 
        llm_service: LLMService,
        provider_registry: Optional[ProviderRegistry] = None
    ):
        """
        Initialize the agent factory.
        
        Args:
            smart_library: Smart library for retrieving agent records
            llm_service: LLM service for text generation
            provider_registry: Optional provider registry to use
        """
        self.library = smart_library
        self.llm_service = llm_service
        self.active_agents = {}
        
        # Initialize or use provided provider registry
        self.provider_registry = provider_registry or ProviderRegistry()
        
        # Register default providers if not already registered
        if not self.provider_registry.list_available_providers():
            self._register_default_providers()
        
        logger.info(f"Agent Factory initialized with providers: {self.provider_registry.list_available_providers()}")
    
    def _register_default_providers(self) -> None:
        """Register the default set of providers."""
        # Register BeeAI provider
        self.provider_registry.register_provider(BeeAIProvider(self.llm_service))
        
        # Additional providers would be registered here
        
        logger.info(f"Registered default providers: {self.provider_registry.list_available_providers()}")
    
    async def create_agent(
        self, 
        record: Dict[str, Any],
        firmware_content: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Create an agent instance from a library record.
        
        Args:
            record: Agent record from the Smart Library
            firmware_content: Optional firmware content to inject
            tools: Optional list of tools to provide to the agent
            config: Optional configuration parameters
            
        Returns:
            Instantiated agent
        """
        # Extract framework name from record metadata
        metadata = record.get("metadata", {})
        framework_name = metadata.get("framework", "default")
        
        # Apply default config
        config = config or {}
        
        logger.info(f"Creating agent '{record['name']}' using framework '{framework_name}'")
        
        # Get the appropriate provider
        provider = self.provider_registry.get_provider_for_framework(framework_name)
        
        if not provider:
            # If no specific provider found, use a default implementation or raise an error
            error_msg = f"No provider found for framework '{framework_name}'"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Create the agent using the provider
            agent_instance = await provider.create_agent(
                record=record,
                tools=tools,
                firmware_content=firmware_content,
                config=config
            )
            
            # Store in active agents with information about its provider
            self.active_agents[record["name"]] = {
                "record": record,
                "instance": agent_instance,
                "type": "AGENT",
                "framework": framework_name,
                "provider_id": provider.__class__.__name__
            }
            
            logger.info(f"Successfully created agent '{record['name']}' with framework '{framework_name}'")
            return agent_instance
            
        except Exception as e:
            logger.error(f"Error creating agent '{record['name']}': {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def execute_agent(
        self, 
        agent_name: str, 
        input_text: str,
        execution_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an agent by name with input text.
        
        Args:
            agent_name: Name of the agent to execute
            input_text: Input text to process
            execution_config: Optional execution configuration parameters
            
        Returns:
            Execution result dictionary
        """
        if agent_name not in self.active_agents:
            error_msg = f"Agent '{agent_name}' not found in active agents"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        
        agent_info = self.active_agents[agent_name]
        agent_instance = agent_info["instance"]
        framework_name = agent_info.get("framework", "default")
        
        logger.info(f"Executing agent '{agent_name}' using framework '{framework_name}'")
        
        # Get the appropriate provider
        provider = self.provider_registry.get_provider_for_framework(framework_name)
        
        if not provider:
            error_msg = f"No provider found for framework '{framework_name}'"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        
        try:
            # Execute the agent using the provider
            result = await provider.execute_agent(
                agent_instance=agent_instance,
                input_text=input_text,
                execution_config=execution_config
            )
            
            # Update usage metrics if available
            if hasattr(self.library, "update_usage_metrics") and "record" in agent_info:
                await self.library.update_usage_metrics(
                    agent_info["record"]["id"], 
                    result["status"] == "success"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing agent '{agent_name}': {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "status": "error",
                "message": f"Error executing agent '{agent_name}': {str(e)}"
            }
    
    async def execute_agent_instance(
        self, 
        agent_instance: Any, 
        input_text: str,
        framework_name: str,
        execution_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an agent instance directly.
        
        Args:
            agent_instance: The agent instance to execute
            input_text: Input text to process
            framework_name: Name of the framework the agent belongs to
            execution_config: Optional execution configuration parameters
            
        Returns:
            Execution result dictionary
        """
        logger.info(f"Executing agent instance using framework '{framework_name}'")
        
        # Get the appropriate provider
        provider = self.provider_registry.get_provider_for_framework(framework_name)
        
        if not provider:
            error_msg = f"No provider found for framework '{framework_name}'"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        
        try:
            # Execute the agent using the provider
            return await provider.execute_agent(
                agent_instance=agent_instance,
                input_text=input_text,
                execution_config=execution_config
            )
            
        except Exception as e:
            logger.error(f"Error executing agent instance: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "status": "error",
                "message": f"Error executing agent instance: {str(e)}"
            }
    
    def get_available_frameworks(self) -> List[str]:
        """
        Get a list of available framework names.
        
        Returns:
            List of framework names
        """
        frameworks = set()
        
        # Collect all framework names that registered providers support
        for provider in self.provider_registry.get_all_providers():
            frameworks.update(provider.get_supported_agent_types())
        
        return list(frameworks)
    
    def get_agent_creation_schema(self, framework_name: str) -> Dict[str, Any]:
        """
        Get the schema for agent creation configuration.
        
        Args:
            framework_name: Name of the framework to get the schema for
            
        Returns:
            Configuration schema for the specified framework
        """
        provider = self.provider_registry.get_provider_for_framework(framework_name)
        
        if not provider:
            return {}
        
        return provider.get_configuration_schema()