from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.models import TranscodeTaskDB, ConfigTemplateDB
from models.schemas import TaskStatus, TranscodeConfig, MediaMetadata, ConfigTemplateRequest, ConfigTemplateResponse
from typing import Optional, Dict, List
import json
import uuid
from datetime import datetime


class TaskCRUD:
    @staticmethod
    async def create_task(
        db: AsyncSession,
        task_id: str,
        source_url: str,
        source_key: Optional[str],
        config: TranscodeConfig,
        callback_url: Optional[str] = None,
        callback_auth: Optional[Dict] = None,
        pubsub_topic: Optional[str] = None
    ) -> TranscodeTaskDB:
        """Create new transcode task"""
        task = TranscodeTaskDB(
            task_id=task_id,
            source_url=source_url,
            source_key=source_key,
            config=config.model_dump(),
            status=TaskStatus.PENDING,
            callback_url=callback_url,
            callback_auth=callback_auth,
            pubsub_topic=pubsub_topic
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task
    
    @staticmethod
    async def get_task(db: AsyncSession, task_id: str) -> Optional[TranscodeTaskDB]:
        """Get task by ID"""
        result = await db.execute(
            select(TranscodeTaskDB).where(TranscodeTaskDB.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None
    ) -> Optional[TranscodeTaskDB]:
        """Update task status"""
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                status=status,
                error_message=error_message,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    
    async def add_task_output(
        db: AsyncSession,
        task_id: str,
        profile_id: str,
        output_urls: List[str],
        metadata: Optional[List[MediaMetadata]] = None
    ) -> Optional[TranscodeTaskDB]:
        """Add output URLs and metadata for a profile"""
        task = await TaskCRUD.get_task(db, task_id)
        if not task:
            return None
        
        outputs = task.outputs or {}
        
        # If we have metadata, store URLs with metadata
        if metadata:
            output_with_metadata = []
            for i, url in enumerate(output_urls):
                meta_dict = metadata[i].model_dump() if i < len(metadata) else {}
                output_with_metadata.append({
                    "url": url,
                    "metadata": meta_dict
                })
            outputs[profile_id] = output_with_metadata
        else:
            # Fallback to URL-only format for backward compatibility
            outputs[profile_id] = output_urls
        
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                outputs=outputs,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    async def clear_task_results(
        db: AsyncSession,
        task_id: str
    ) -> Optional[TranscodeTaskDB]:
        """Clear outputs and failed profiles for task retry"""
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                outputs=None,
                failed_profiles=None,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    
    async def add_failed_profile(
        db: AsyncSession,
        task_id: str,
        profile_id: str,
        error_message: str
    ) -> Optional[TranscodeTaskDB]:
        """Add failed profile information"""
        task = await TaskCRUD.get_task(db, task_id)
        if not task:
            return None
        
        failed_profiles = task.failed_profiles or {}
        failed_profiles[profile_id] = {
            "error_message": error_message,
            "failed_at": datetime.utcnow().isoformat()
        }
        
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                failed_profiles=failed_profiles,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    
    async def get_tasks_by_status(
        db: AsyncSession,
        status: TaskStatus,
        limit: int = 100
    ) -> List[TranscodeTaskDB]:
        """Get tasks by status"""
        result = await db.execute(
            select(TranscodeTaskDB)
            .where(TranscodeTaskDB.status == status)
            .order_by(TranscodeTaskDB.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    
    async def mark_task_completed(
        db: AsyncSession,
        task_id: str
    ) -> Optional[TranscodeTaskDB]:
        """Mark task as completed if all profiles are done"""
        task = await TaskCRUD.get_task(db, task_id)
        if not task:
            return None
        
        config = TranscodeConfig(**task.config)
        expected_profiles = len(config.profiles)
        
        if task.outputs and len(task.outputs) >= expected_profiles:
            return await TaskCRUD.update_task_status(db, task_id, TaskStatus.COMPLETED)
        
        return task
    
    @staticmethod
    
    async def get_tasks_optimized(
        db: AsyncSession,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TranscodeTaskDB]:
        """Optimized method to get tasks with pagination"""
        query = select(TranscodeTaskDB)
        
        if status:
            query = query.where(TranscodeTaskDB.status == status)
        
        query = query.order_by(TranscodeTaskDB.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def update_face_detection_status(
        db: AsyncSession,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None
    ) -> Optional[TranscodeTaskDB]:
        """Update face detection status"""
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                face_detection_status=status,
                face_detection_error=error_message,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    async def add_face_detection_results(
        db: AsyncSession,
        task_id: str,
        results: Dict
    ) -> Optional[TranscodeTaskDB]:
        """Add face detection results"""
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                face_detection_results=results,
                face_detection_status=TaskStatus.COMPLETED,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    async def reset_failed_task(
        db: AsyncSession,
        task_id: str
    ) -> Optional[TranscodeTaskDB]:
        """Reset a failed/completed task to initial state for retry"""
        stmt = (
            update(TranscodeTaskDB)
            .where(TranscodeTaskDB.task_id == task_id)
            .values(
                status=TaskStatus.PENDING,
                outputs=None,
                failed_profiles=None,
                error_message=None,
                face_detection_status=None,
                face_detection_error=None,
                face_detection_results=None,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return await TaskCRUD.get_task(db, task_id)
    
    @staticmethod
    async def mark_task_completed_check_all(
        db: AsyncSession,
        task_id: str
    ) -> Optional[TranscodeTaskDB]:
        """Mark task as completed if both transcode and face detection are done"""
        task = await TaskCRUD.get_task(db, task_id)
        if not task:
            return None
        
        config = TranscodeConfig(**task.config)
        expected_profiles = len(config.profiles)
        
        # Check if transcode is complete (including partial completion with failures)
        completed_profiles = len(task.outputs) if task.outputs else 0
        failed_profiles = len(task.failed_profiles) if task.failed_profiles else 0
        total_processed = completed_profiles + failed_profiles
        
        transcode_complete = total_processed >= expected_profiles and completed_profiles > 0
        
        # Check if face detection is complete (if enabled)
        face_detection_enabled = (
            config.face_detection_config and 
            config.face_detection_config.enabled
        )
        
        if face_detection_enabled:
            face_detection_complete = task.face_detection_status == TaskStatus.COMPLETED
            
            # Both must be complete
            if transcode_complete and face_detection_complete:
                # Add error message if there are failed profiles
                error_msg = None
                if failed_profiles > 0:
                    error_msg = f"Completed with {failed_profiles} failed profile(s) out of {expected_profiles}"
                
                return await TaskCRUD.update_task_status(db, task_id, TaskStatus.COMPLETED, error_message=error_msg)
        else:
            # Only transcode needs to be complete
            if transcode_complete:
                # Add error message if there are failed profiles
                error_msg = None
                if failed_profiles > 0:
                    error_msg = f"Completed with {failed_profiles} failed profile(s) out of {expected_profiles}"
                
                return await TaskCRUD.update_task_status(db, task_id, TaskStatus.COMPLETED, error_message=error_msg)
        
        return task


class ConfigTemplateCRUD:
    @staticmethod
    async def create_template(
        db: AsyncSession,
        request: ConfigTemplateRequest
    ) -> ConfigTemplateResponse:
        """Create new config template"""
        template_id = str(uuid.uuid4())
        template = ConfigTemplateDB(
            template_id=template_id,
            name=request.name,
            config=[profile.model_dump() for profile in request.config]
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        return ConfigTemplateResponse(
            template_id=template.template_id,
            name=template.name,
            config=request.config,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
    
    @staticmethod
    async def get_template(db: AsyncSession, template_id: str) -> Optional[ConfigTemplateDB]:
        """Get template by ID"""
        result = await db.execute(
            select(ConfigTemplateDB).where(ConfigTemplateDB.template_id == template_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_templates(db: AsyncSession) -> List[ConfigTemplateDB]:
        """Get all templates"""
        result = await db.execute(
            select(ConfigTemplateDB).order_by(ConfigTemplateDB.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_template(
        db: AsyncSession,
        template_id: str,
        request: ConfigTemplateRequest
    ) -> Optional[ConfigTemplateResponse]:
        """Update existing template"""
        stmt = (
            update(ConfigTemplateDB)
            .where(ConfigTemplateDB.template_id == template_id)
            .values(
                name=request.name,
                config=[profile.model_dump() for profile in request.config],
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        template = await ConfigTemplateCRUD.get_template(db, template_id)
        if template:
            return ConfigTemplateResponse(
                template_id=template.template_id,
                name=template.name,
                config=request.config,
                created_at=template.created_at,
                updated_at=template.updated_at
            )
        return None
    
    @staticmethod
    async def delete_template(db: AsyncSession, template_id: str) -> bool:
        """Delete template"""
        template = await ConfigTemplateCRUD.get_template(db, template_id)
        if template:
            await db.delete(template)
            await db.commit()
            return True
        return False