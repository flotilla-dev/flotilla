# tests/test_flotilla_container.py
import pytest
import os
import tempfile
import yaml
from pathlib import Path

from flotilla.container.flotilla_container import FlotillaContainer


class TestFlotillaContainer:
    """Test suite for FlotillaContainer configuration loading"""
    
    @pytest.fixture
    def config_dir(self):
        """Create temporary config directory with test YAML files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)
            
            # Create flotilla.yml
            flotilla_config = {
                'flotilla': {
                    'llm': {
                        'type': 'openai',
                        'model': 'gpt-4o-mini',
                        'temperature': 0.7,
                        'api_key': '${OPENAI_API_KEY}'
                    },
                    'tool_registry': {
                        'enable_discovery': True,
                        'packages': ['flotilla.tools']
                    },
                    'agent_registry': {
                        'enable_discovery': True,
                        'packages': ['flotilla.agents']
                    }
                }
            }
            with open(config_path / 'flotilla.yml', 'w') as f:
                yaml.dump(flotilla_config, f)
            
            # Create flotilla.prod.yml (override)
            flotilla_prod_config = {
                'flotilla': {
                    'llm': {
                        'model': 'gpt-4',
                        'temperature': 0.5
                    }
                }
            }
            with open(config_path / 'flotilla.prod.yml', 'w') as f:
                yaml.dump(flotilla_prod_config, f)
            
            # Create agents.yml
            agents_config = {
                'agents': {
                    'research_agent': {
                        'type': 'research',
                        'llm': {
                            'temperature': 0.9
                        },
                        'tools': ['web_search']
                    },
                    'sales_agent': {
                        'type': 'sales',
                        'tools': ['crm']
                    }
                }
            }
            with open(config_path / 'agents.yml', 'w') as f:
                yaml.dump(agents_config, f)
            
            # Create tools.yml
            tools_config = {
                'tools': {
                    'web_search': {
                        'type': 'langchain_decorator',
                        'enabled': True
                    }
                }
            }
            with open(config_path / 'tools.yml', 'w') as f:
                yaml.dump(tools_config, f)
            
            # Create feature_flags.yml
            feature_flags_config = {
                'feature_flags': {
                    'enable_experimental': False
                }
            }
            with open(config_path / 'feature_flags.yml', 'w') as f:
                yaml.dump(feature_flags_config, f)
            
            yield str(config_path)
    
    def test_container_creation(self):
        """Test that container can be created"""
        container = FlotillaContainer()
        assert container is not None
        assert container.config is not None
    
    def test_container_start_with_defaults(self, config_dir, monkeypatch):
        """Test container starts with default environment"""
        # Set APP_ENV
        monkeypatch.setenv("APP_ENV", "LOCAL")
        
        container = FlotillaContainer()
        container.start(config_dir=config_dir)
        
        # Verify config loaded
        assert container.config.flotilla.llm.model() == 'gpt-4o-mini'
        assert container.config.flotilla.llm.temperature() == 0.7
    
    def test_container_start_with_prod_environment(self, config_dir):
        """Test container starts with PROD environment and overrides apply"""
        container = FlotillaContainer()
        container.start(env="PROD", config_dir=config_dir)
        
        # Verify prod overrides applied
        assert container.config.flotilla.llm.model() == 'gpt-4'  # Overridden
        assert container.config.flotilla.llm.temperature() == 0.5  # Overridden
        assert container.config.flotilla.llm.type() == 'openai'  # Inherited
    
    def test_container_loads_all_config_files(self, config_dir):
        """Test that all config files are loaded"""
        container = FlotillaContainer()
        container.start(config_dir=config_dir)
        
        # Verify flotilla config
        assert container.config.flotilla.llm.model() is not None
        
        # Verify agents config
        agents = container.config.agents()
        assert 'research_agent' in agents
        assert 'sales_agent' in agents
        
        # Verify tools config
        tools = container.config.tools()
        assert 'web_search' in tools
        
        # Verify feature flags
        assert container.config.feature_flags.enable_experimental() == False
    
    def test_container_env_var_substitution(self, config_dir, monkeypatch):
        """Test environment variable substitution"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-123")
        
        container = FlotillaContainer()
        container.start(config_dir=config_dir)
        
        # Verify env var was substituted
        api_key = container.config.flotilla.llm.api_key()
        assert api_key == "test-api-key-123"
    
    def test_container_missing_env_file_not_required(self, config_dir):
        """Test that missing environment-specific files don't cause errors"""
        container = FlotillaContainer()
        
        # Should not raise - dev file doesn't exist but is not required
        container.start(env="DEV", config_dir=config_dir)
        
        # Should load base config
        assert container.config.flotilla.llm.model() == 'gpt-4o-mini'
    
    def test_container_custom_config_dir(self, config_dir):
        """Test that custom config directory works"""
        container = FlotillaContainer()
        container.start(config_dir=config_dir)
        
        assert container.config.flotilla.llm.model() is not None
    
    def test_container_uses_app_env_variable(self, config_dir, monkeypatch):
        """Test that APP_ENV environment variable is used when env not specified"""
        monkeypatch.setenv("APP_ENV", "PROD")
        
        container = FlotillaContainer()
        container.start(config_dir=config_dir)
        
        # Should use PROD config
        assert container.config.flotilla.llm.model() == 'gpt-4'
    
    def test_container_nested_config_access(self, config_dir):
        """Test accessing nested configuration values"""
        container = FlotillaContainer()
        container.start(config_dir=config_dir)
        
        # Test nested access
        research_agent = container.config.agents.research_agent()
        assert research_agent['type'] == 'research'
        assert research_agent['llm']['temperature'] == 0.9
        assert 'web_search' in research_agent['tools']
    
    def test_container_config_merging(self, config_dir):
        """Test that configuration merging works correctly"""
        container = FlotillaContainer()
        container.start(env="PROD", config_dir=config_dir)
        
        # Values from prod should override
        assert container.config.flotilla.llm.model() == 'gpt-4'
        assert container.config.flotilla.llm.temperature() == 0.5
        
        # Values not in prod should come from base
        assert container.config.flotilla.llm.type() == 'openai'
        assert container.config.flotilla.tool_registry.enable_discovery() == True