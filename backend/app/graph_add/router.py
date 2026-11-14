"""HTTP routes for the Graph Add section.

Mounted at ``/api/graph-add``. A document is offered a ranked set of homes first, then
placed once the user picks one — so the person, not the caller's guess, decides where the
file lands. Suggestions are scored locally (no model call); placement writes one row and then
refreshes the affected folder descriptions in a single model call.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.graph_add.describer import build_describer
from app.graph_add.repository import SupabaseAddRepository
from app.graph_add.schemas import PlacementIn, PlacementOut, SuggestionAccepted
from app.graph_add.service import GraphAddService
from app.graph_add.storage import SupabaseObjectStore

router = APIRouter(tags=["Graph Add"])


def get_service() -> GraphAddService:
    """Wire the service for a request (Supabase repository + storage + folder describer)."""
    settings = get_settings()
    return GraphAddService(
        repository=SupabaseAddRepository(),
        store=SupabaseObjectStore(bucket=settings.storage_bucket),
        describer=build_describer(settings),
        settings=settings,
    )


ServiceDep = Annotated[GraphAddService, Depends(get_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post(
    "/suggestions",
    response_model=SuggestionAccepted,
    summary="Suggest where a new document belongs",
)
async def create_suggestion(
    user: UserDep,
    service: ServiceDep,
    file: Annotated[
        UploadFile,
        File(description="A single markdown document (.md, .markdown or .mdx)."),
    ],
    project_id: Annotated[str, Form(description="Project the document should join.")],
) -> SuggestionAccepted:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="the uploaded file is empty"
        )
    if len(data) > settings.max_file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"the file is larger than the {settings.max_file_bytes} byte limit",
        )

    result = await service.suggest(
        owner_id=user.id,
        project_id=project_id,
        filename=file.filename or "",
        data=data,
    )
    return SuggestionAccepted(**result)


@router.post(
    "/placements",
    status_code=status.HTTP_201_CREATED,
    response_model=PlacementOut,
    summary="Place a suggested document in the chosen directory",
)
async def create_placement(
    payload: PlacementIn, user: UserDep, service: ServiceDep
) -> PlacementOut:
    result = await service.place(
        owner_id=user.id,
        request_id=payload.request_id,
        directory_id=payload.directory_id,
        placement=payload.placement,
        new_directory_name=payload.new_directory_name,
        file_name=payload.file_name,
    )
    return PlacementOut(**result)


@router.get(
    "/suggestions/{request_id}",
    response_model=SuggestionAccepted,
    summary="Re-read a suggestion you were shown earlier",
)
async def get_suggestion(request_id: str, user: UserDep, service: ServiceDep) -> SuggestionAccepted:
    return SuggestionAccepted(**await service.get_request(request_id, user.id))
