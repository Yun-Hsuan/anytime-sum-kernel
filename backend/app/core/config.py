import os
from pathlib import Path
import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def get_env_files() -> list[str]:
    """Get the appropriate .env files based on the environment.
    Returns a list of env files in order of precedence (later files override earlier ones).
    """
    # Get the project root directory
    current_file = Path(__file__).resolve()
    working_dir = Path(os.getcwd())
    
    print(f"Current file path: {current_file}")
    print(f"Working directory: {working_dir}")
    print(f"Environment variable ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
    
    env_files = []
    
    # First check for mounted .env file
    mounted_env = working_dir / ".env"
    print(f"Checking for mounted .env file at: {mounted_env}")
    print(f"Mounted .env exists: {mounted_env.exists()}")
    if mounted_env.exists():
        print(f"Found mounted .env file at: {mounted_env}")
        env_files.append(str(mounted_env))
        return env_files
    
    # If no mounted .env file, try environment specific file
    env_type = os.getenv("ENVIRONMENT", "local")
    if env_type in ["local", "staging", "production"]:
        env_file = working_dir / "env-config" / env_type / ".env"
        print(f"Checking for environment file at: {env_file}")
        print(f"Environment file exists: {env_file.exists()}")
        if env_file.exists():
            print(f"Found environment specific file at: {env_file}")
            env_files.append(str(env_file))
    
    if not env_files:
        warnings.warn("No .env files found!", stacklevel=2)
    
    print(f"Using env files in order (later files override earlier ones): {env_files}")
    return env_files


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_files(),  # Now accepts a list of files
        env_ignore_empty=True,
        extra="ignore",
    )
    
    # Move ENVIRONMENT to the top since it's critical for configuration
    ENVIRONMENT: Literal["local", "staging", "production"] = os.getenv("ENVIRONMENT", "local")
    
    print(f"Settings ENVIRONMENT value: {ENVIRONMENT}")
    
    # Debug settings
    DEBUG_SQL: bool = False  # Default to False, can be overridden in .env file

    # Azure OpenAI settings
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str 
    AZURE_OPENAI_API_VERSION: str = "2024-07-18-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o-mini"
    
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        return self


print("Initializing Settings...")
settings = Settings()  # type: ignore
print("Settings initialized successfully")
