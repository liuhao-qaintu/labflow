from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import Field
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent #后端项目的根路径


class Settings(BaseSettings):
    DATABASE_URL:str
    JWT_SECRET_KEY:str = Field(min_length=1)
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM :str = "HS256"
    LLM_BASE_URL :str
    LLM_MODEL :str
    SILICONFLOW_API_KEY: str = ""
    ENABLE_API_DOCS: bool = False
    DEVELOPER_USER_IDS: list[int] = []
    PASSWORD_RECOVERY_ADMIN_ID: int | None = None
    RESET_INITIAL_PASSWORD: str = ""

    model_config= SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

settings = Settings()


MAX_FILE_SIZE = 100*1024*1024
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)

ALLOW_EXTENSIONS = {
    ".jpg",".jpeg",".png",".gif",".webp",".pdf",
    ".doc",".docx",".xls",".xlsx",".zip"
}


