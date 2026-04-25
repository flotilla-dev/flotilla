from pydantic import BaseModel, Field


class FastAPIRunConfig(BaseModel):
    host: str = Field(default="127.0.0.1", description="Host interface to bind the FastAPI server to")
    port: int = Field(default=8000, description="Port to bind the FastAPI server to")
    log_level: str = Field(default="info", description="Log level used by the FastAPI server")
    reload: bool = Field(default=False, description="Whether to enable auto-reload for development")
