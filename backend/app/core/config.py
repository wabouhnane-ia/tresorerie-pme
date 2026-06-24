from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ---------------------------------
    # Application
    # ---------------------------------

    APP_NAME: str

    APP_VERSION: str

    DEBUG: bool = True


    # ---------------------------------
    # API
    # ---------------------------------

    API_HOST: str

    API_PORT: int


    # ---------------------------------
    # OpenRouter
    # ---------------------------------

    OPENROUTER_API_KEY: str


    # ---------------------------------
    # MongoDB
    # ---------------------------------

    MONGODB_URL: str

    MONGODB_DB: str


    # ---------------------------------
    # JWT
    # ---------------------------------

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    STORAGE_ROOT: str = "storage"
    
    # ---------------------------------
    # Historical Depth Tolerance
    # ---------------------------------
    
    MIN_HISTORY_MONTHS: int = 24
    HISTORY_TOLERANCE: float = 0.1
    ADVANCED_HISTORY_MONTHS: int = 36
    EXCELLENT_HISTORY_MONTHS: int = 48


    # ---------------------------------
    # ENV
    # ---------------------------------

    class Config:

        env_file = ".env"


settings = Settings()