from pydantic import BaseModel
from config.flotilla_setttings import FlotillaSettings
from config.application_settings import ApplicationSettings


class Settings(BaseModel):
    """
    Root settings object combining framework and application settings.
    """
    flotilla: FlotillaSettings
    application: ApplicationSettings

  
