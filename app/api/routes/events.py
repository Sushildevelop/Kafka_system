from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.schemas.event import EventCreate, EventPublishedResponse, EventResponse
from app.services.event_service import create_event, list_events
from app.services.kafka_producer import KafkaUnavailableError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventPublishedResponse, status_code=status.HTTP_202_ACCEPTED)
async def publish_event_route(event: EventCreate, request: Request) -> EventPublishedResponse:
    try:
        return await create_event(event, request.app.state.kafka_producer)
    except KafkaUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("", response_model=list[EventResponse])
async def get_events(
    request: Request,
    response: Response,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    consistency: Literal["eventual", "strong"] = Query(default="eventual"),
) -> list[EventResponse]:
    try:
        events = await list_events(
            request.app.state.event_repository,
            skip=skip,
            limit=limit,
            consistency=consistency,
        )
        response.headers["X-Read-Target"] = (
            "primary" if consistency == "strong" else "replica-preferred"
        )
        return events
    except Exception as exc:
        logger.exception("Could not fetch events from MongoDB")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is unavailable",
        ) from exc
