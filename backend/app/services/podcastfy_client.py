"""
Adapter module for podcastfy integration.
This module provides a clean interface to the podcastfy library while allowing easy updates.
"""

from typing import Dict, Optional
from pathlib import Path
import os
from datetime import datetime
from podcastfy.client import generate_podcast as podcastfy_generate
from podcastfy.config import PodcastConfig as BasePodcastConfig
from app.core.logger import get_logger

logger = get_logger(__name__)

class PodcastConfig(BasePodcastConfig):
    """Extended podcast configuration with SurfSense-specific settings."""
    
    @classmethod
    def create_default(cls, word_count: int = 500) -> "PodcastConfig":
        """Create default podcast configuration."""
        return cls(
            word_count=word_count,
            podcast_name="SurfSense Podcast",
            podcast_tagline="Your Personal AI Podcast",
            output_language="English",
            user_instructions="Make it engaging and informative",
            engagement_techniques=[
                "Rhetorical Questions",
                "Personal Testimonials",
                "Quotes",
                "Anecdotes",
                "Analogies",
                "Humor"
            ]
        )

class PodcastGenerator:
    """Wrapper for podcastfy functionality."""
    
    def __init__(self, output_dir: str = "podcasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    async def generate_podcast(
        self,
        content: str,
        model_name: str,
        word_count: int = 500,
        api_key: Optional[str] = None,
        config: Optional[PodcastConfig] = None
    ) -> str:
        """
        Generate a podcast from text content.
        
        Args:
            content: Text content to convert to podcast
            model_name: Name of the LLM model to use
            word_count: Target word count for the podcast
            api_key: Optional API key for the LLM
            config: Optional custom podcast configuration
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Use default config if none provided
            if not config:
                config = PodcastConfig.create_default(word_count)
            
            # Generate podcast using podcastfy
            temp_file_path = podcastfy_generate(
                text=content,
                llm_model_name=model_name,
                api_key_label=api_key if api_key else "OPENAI_API_KEY",
                conversation_config=config.dict(),
            )
            
            # Move to permanent storage with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_path = self.output_dir / f"podcast_{timestamp}.mp3"
            os.rename(temp_file_path, final_path)
            
            logger.info(f"Generated podcast saved to {final_path}")
            return str(final_path)
            
        except Exception as e:
            logger.error(f"Error generating podcast: {str(e)}")
            raise

    def cleanup_file(self, file_path: str) -> None:
        """
        Clean up a podcast file.
        
        Args:
            file_path: Path to the file to delete
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted podcast file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting podcast file {file_path}: {str(e)}")
            # Don't raise the error as this is a cleanup operation
