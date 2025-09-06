from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Pub/Sub
    pubsub_project_id: str
    pubsub_tasks_topic: str
    tasks_subscription: str
    pubsub_results_topic: str
    pubsub_results_subscription: str
    pubsub_publisher_credentials_path: str
    pubsub_subscriber_credentials_path: str
    
    # AWS S3
    aws_endpoint_public_url: str
    aws_endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_bucket_name: str
    aws_base_folder: str

    # Database
    database_url: str

    # PostgreSQL specific settings
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "transcode_db"
    postgres_user: str = "transcode_user"
    postgres_password: str = "transcode_pass"

    @property
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields instead of raising error


settings = Settings()
