from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Pub/Sub
    pubsub_project_id: str = ""
    pubsub_tasks_topic: str = ""
    tasks_subscription: str = ""
    pubsub_results_topic: str = ""
    pubsub_results_subscription: str = ""
    pubsub_publisher_credentials_path: str = ""
    pubsub_subscriber_credentials_path: str = ""
    disable_pubsub: bool = False
    google_application_credentials: str = ""

    # Face Detection PubSub
    face_detection_subscription: str = ""
    pubsub_face_detection_tasks_topic: str = ""
    pubsub_face_detection_results_topic: str = ""
    pubsub_face_detection_results_subscription: str = ""

    # AWS S3
    aws_endpoint_public_url: str = ""
    aws_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_bucket_name: str = ""
    aws_base_folder: str = ""

    # Database
    database_url: str = (
        "postgresql+asyncpg://transcode_user:transcode_pass@localhost:5433/transcode_db"
    )

    # PostgreSQL specific settings (Docker services)
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "transcode_db"
    postgres_user: str = "transcode_user"
    postgres_password: str = "transcode_pass"

    @property
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{
        self.postgres_user}:{
        self.postgres_password}@{
        self.postgres_host}:{
        self.postgres_port}/{
        self.postgres_db}"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # FFmpeg Configuration
    ffmpeg_path: str = "/usr/bin/ffmpeg"
    ffprobe_path: str = "/usr/bin/ffprobe"
    ffmpeg_hwaccel: str = "none"
    ffmpeg_gpu_enabled: str = "false"  # Can be "true", "false", or "auto"
    gpu_enabled: bool = False
    gpu_type: str = "none"

    @field_validator("ffmpeg_gpu_enabled")
    @classmethod
    def validate_ffmpeg_gpu_enabled(cls, v):
        if isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, str) and v.lower() in ["true", "false", "auto"]:
            return v.lower()
        raise ValueError('ffmpeg_gpu_enabled must be "true", "false", or "auto"')

    @property
    def is_gpu_enabled(self) -> bool:
        """Check if GPU is enabled (handles auto detection)"""
        if self.ffmpeg_gpu_enabled == "auto":
            # Auto-detect GPU availability (simplified logic)
            return self.gpu_enabled
        return self.ffmpeg_gpu_enabled == "true"

    # Storage
    temp_storage_path: str = "/tmp/transcode"
    shared_volume_path: str = "/shared/media"

    # Legacy attribute names for backward compatibility
    @property
    def AWS_ACCESS_KEY_ID(self) -> str:
        return self.aws_access_key_id

    @property
    def AWS_SECRET_ACCESS_KEY(self) -> str:
        return self.aws_secret_access_key

    @property
    def AWS_REGION(self) -> str:
        return "us-east-1"  # Default region

    @property
    def S3_BUCKET(self) -> str:
        return self.aws_bucket_name

    @property
    def TEMP_STORAGE_PATH(self) -> str:
        return self.temp_storage_path

    @property
    def FFMPEG_PATH(self) -> str:
        return self.ffmpeg_path

    @property
    def FFPROBE_PATH(self) -> str:
        return self.ffprobe_path

    @property
    def GPU_ENABLED(self) -> bool:
        return self.gpu_enabled

    @property
    def GPU_TYPE(self) -> str:
        return self.gpu_type

    # Flask configuration
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """SQLAlchemy database URI for Flask"""
        if self.database_url:
            return self.database_url
        return self.postgres_url

    @property
    def SQLALCHEMY_TRACK_MODIFICATIONS(self) -> bool:
        return False

    @property
    def DEBUG(self) -> bool:
        return True

    @property
    def UPLOAD_FOLDER(self) -> str:
        return "uploads"

    @property
    def SECRET_KEY(self) -> str:
        return "dev-secret-key-change-in-production"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields instead of raising error


settings = Settings()


def get_config():
    """Get configuration settings instance"""
    return settings
