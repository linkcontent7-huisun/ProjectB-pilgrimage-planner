import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    NAVER_MAP_CLIENT_ID: str = os.getenv("NAVER_MAP_CLIENT_ID", "")
    NAVER_MAP_CLIENT_SECRET: str = os.getenv("NAVER_MAP_CLIENT_SECRET", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]


settings = Settings()
