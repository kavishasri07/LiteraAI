from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "LiteraAI"
    database_path: str = "data/literaai.db"
    upload_dir: str = "data/uploads"
    max_upload_mb: int = 30
    chunk_size: int = 1100
    chunk_overlap: int = 180
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout_seconds: int = 90
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def db_file(self) -> Path:
        return (BASE_DIR / self.database_path).resolve()

    @property
    def uploads_path(self) -> Path:
        return (BASE_DIR / self.upload_dir).resolve()

settings = Settings()
