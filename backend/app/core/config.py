"""Application settings loaded from environment variables.

All environment-specific configuration lives here so source code
never hardcodes hosts, ports, or secrets (spec section 18).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Intelligent Timetable Generator"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/timetable"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/timetable_test"
    # BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    BACKEND_CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:8000,"
        "http://127.0.0.1:8000"
    )

    # Auth — no defaults for the secret: it must come from the environment.
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Timetable solver (OR-Tools CP-SAT runs locally; no cloud/service needed).
    TIMETABLE_SOLVER_TIME_LIMIT_SECONDS: int = 30
    TIMETABLE_SOLVER_NUM_WORKERS: int = 4
    TIMETABLE_SOLVER_RANDOM_SEED: int = 42

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
