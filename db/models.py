from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from models.schemas import TaskStatus
import uuid

Base = declarative_base()


class TranscodeTaskDB(Base):
    __tablename__ = "transcode_tasks"
    
    task_id = Column(String, primary_key=True, index=True)
    source_url = Column(String, nullable=False)
    source_key = Column(String, nullable=True)  # Nullable for URL inputs
    config = Column(JSON, nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, onupdate=func.now())
    error_message = Column(Text, nullable=True)
    outputs = Column(JSON, nullable=True)
    failed_profiles = Column(JSON, nullable=True)  # Store failed profile information
    callback_url = Column(String, nullable=True)
    callback_auth = Column(JSON, nullable=True)  # Store auth headers/tokens
    pubsub_topic = Column(String, nullable=True)  # PubSub topic for notifications
    
    # Face detection fields
    face_detection_status = Column(SQLEnum(TaskStatus), nullable=True, index=True)  # Status of face detection task
    face_detection_results = Column(JSON, nullable=True)  # Face detection results
    face_detection_error = Column(Text, nullable=True)  # Face detection error message
    
    def to_dict(self):
        return {
            "task_id": self.task_id,
            "source_url": self.source_url,
            "source_key": self.source_key,
            "config": self.config,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "outputs": self.outputs,
            "failed_profiles": self.failed_profiles,
            "callback_url": self.callback_url,
            "callback_auth": self.callback_auth,
            "pubsub_topic": self.pubsub_topic,
            "face_detection_status": self.face_detection_status,
            "face_detection_results": self.face_detection_results,
            "face_detection_error": self.face_detection_error
        }


class ConfigTemplateDB(Base):
    __tablename__ = "config_templates"
    
    template_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())
    
    def to_dict(self):
        return {
            "template_id": self.template_id,
            "name": self.name,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }