from flotilla.config.configuration_source import ConfigurationSource
from dotenv import load_dotenv


class LocalEnvSource(ConfigurationSource):

    def load(self):
        load_dotenv()
