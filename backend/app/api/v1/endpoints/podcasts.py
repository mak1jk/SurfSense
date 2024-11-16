from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.podcast import PodcastCreate, PodcastResponse, PodcastUpdate
from app.services.podcast import PodcastService

settings = get_settings()
router = APIRouter()

@router.post("/searchspace/{search_space_id}/podcasts/", response_model=PodcastResponse)
async def create_podcast(
    search_space_id: int,
    podcast_data: PodcastCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new podcast in a search space."""
    # Verify search space ownership
    search_space = db.query(SearchSpace).filter(
        SearchSpace.id == search_space_id,
        SearchSpace.user_id == current_user.id
    ).first()
    if not search_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search space not found or does not belong to the user"
        )

    podcast_service = PodcastService(db)
    return await podcast_service.create_podcast(
        podcast_data=podcast_data,
        search_space_id=search_space_id,
        model_name=settings.SMART_LLM,
        api_key=settings.OPENAI_API_KEY if not settings.IS_LOCAL_SETUP else None
    )

@router.get("/searchspace/{search_space_id}/podcasts/", response_model=List[PodcastResponse])
async def get_search_space_podcasts(
    search_space_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all podcasts in a search space."""
    # Verify search space ownership
    search_space = db.query(SearchSpace).filter(
        SearchSpace.id == search_space_id,
        SearchSpace.user_id == current_user.id
    ).first()
    if not search_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search space not found or does not belong to the user"
        )

    podcast_service = PodcastService(db)
    return await podcast_service.get_search_space_podcasts(search_space_id)

@router.get("/searchspace/{search_space_id}/podcasts/{podcast_id}", response_model=PodcastResponse)
async def get_podcast(
    search_space_id: int,
    podcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific podcast."""
    # Verify search space ownership
    search_space = db.query(SearchSpace).filter(
        SearchSpace.id == search_space_id,
        SearchSpace.user_id == current_user.id
    ).first()
    if not search_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search space not found or does not belong to the user"
        )

    podcast_service = PodcastService(db)
    return await podcast_service.get_podcast(podcast_id)

@router.put("/searchspace/{search_space_id}/podcasts/{podcast_id}", response_model=PodcastResponse)
async def update_podcast(
    search_space_id: int,
    podcast_id: int,
    podcast_data: PodcastUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a podcast."""
    # Verify search space ownership
    search_space = db.query(SearchSpace).filter(
        SearchSpace.id == search_space_id,
        SearchSpace.user_id == current_user.id
    ).first()
    if not search_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search space not found or does not belong to the user"
        )

    podcast_service = PodcastService(db)
    return await podcast_service.update_podcast(podcast_id, podcast_data)

@router.delete("/searchspace/{search_space_id}/podcasts/{podcast_id}")
async def delete_podcast(
    search_space_id: int,
    podcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a podcast."""
    # Verify search space ownership
    search_space = db.query(SearchSpace).filter(
        SearchSpace.id == search_space_id,
        SearchSpace.user_id == current_user.id
    ).first()
    if not search_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search space not found or does not belong to the user"
        )

    podcast_service = PodcastService(db)
    await podcast_service.delete_podcast(podcast_id)
    return {"message": "Podcast deleted successfully"}
