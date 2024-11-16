from typing import Dict, Optional
import os
from pathlib import Path
import asyncio
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.logger import get_logger
from app.models.podcast import Podcast
from app.schemas.podcast import PodcastCreate, PodcastUpdate
from app.services.podcastfy_client import PodcastGenerator, PodcastConfig

settings = get_settings()
logger = get_logger(__name__)

class PodcastService:
    def __init__(self, db: Session):
        self.db = db
        self.generator = PodcastGenerator()

    async def create_podcast(
        self, 
        podcast_data: PodcastCreate,
        search_space_id: int,
        model_name: str,
        api_key: Optional[str] = None
    ) -> Podcast:
        """Create a new podcast."""
        try:
            # Create podcast record
            podcast = Podcast(
                title=podcast_data.title,
                podcast_content=podcast_data.content,
                search_space_id=search_space_id,
                status="pending",
                is_completed=False
            )
            self.db.add(podcast)
            self.db.commit()
            self.db.refresh(podcast)

            # Generate podcast in background
            asyncio.create_task(
                self._generate_podcast(
                    podcast_id=podcast.id,
                    content=podcast_data.content,
                    word_count=podcast_data.word_count,
                    model_name=model_name,
                    api_key=api_key
                )
            )

            return podcast

        except Exception as e:
            logger.error(f"Error creating podcast: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create podcast"
            )

    async def _generate_podcast(
        self,
        podcast_id: int,
        content: str,
        word_count: int,
        model_name: str,
        api_key: Optional[str] = None
    ) -> None:
        """Generate podcast audio file."""
        try:
            # Update podcast status
            podcast = self.db.query(Podcast).filter(Podcast.id == podcast_id).first()
            if not podcast:
                logger.error(f"Podcast {podcast_id} not found")
                return

            podcast.status = "processing"
            self.db.commit()

            # Generate podcast
            file_path = await self.generator.generate_podcast(
                content=content,
                model_name=model_name,
                word_count=word_count,
                api_key=api_key
            )

            # Update podcast record
            podcast.file_location = file_path
            podcast.status = "completed"
            podcast.is_completed = True
            self.db.commit()

        except Exception as e:
            logger.error(f"Error generating podcast {podcast_id}: {str(e)}")
            if podcast:
                podcast.status = "failed"
                podcast.is_completed = False
                self.db.commit()

    async def get_podcast(self, podcast_id: int) -> Podcast:
        """Get podcast by ID."""
        podcast = self.db.query(Podcast).filter(Podcast.id == podcast_id).first()
        if not podcast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Podcast not found"
            )
        return podcast

    async def get_search_space_podcasts(self, search_space_id: int) -> list[Podcast]:
        """Get all podcasts in a search space."""
        return self.db.query(Podcast).filter(
            Podcast.search_space_id == search_space_id
        ).all()

    async def delete_podcast(self, podcast_id: int) -> None:
        """Delete a podcast."""
        podcast = await self.get_podcast(podcast_id)
        
        # Delete audio file if exists
        if podcast.file_location:
            self.generator.cleanup_file(podcast.file_location)
        
        self.db.delete(podcast)
        self.db.commit()

    async def update_podcast(
        self, 
        podcast_id: int, 
        podcast_data: PodcastUpdate
    ) -> Podcast:
        """Update podcast details."""
        podcast = await self.get_podcast(podcast_id)
        
        for field, value in podcast_data.dict(exclude_unset=True).items():
            setattr(podcast, field, value)
        
        self.db.commit()
        self.db.refresh(podcast)
        return podcast
