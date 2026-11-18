from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/invoices"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    gemini_models: str = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash-lite"
    groq_model: str = "openai/gpt-oss-120b"
    tesseract_cmd: str = "tesseract"
    ocr_lang: str = "eng"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10
    max_pdf_pages: int = 20


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)