"""HTTP routes for the Graph Creation section.

Mounted at ``/api/graph-creation``. An upload names a directory: either a new project
tree (``mode=new``, which is also how a re-upload starts over) or an addition to an
existing one (``mode=add``). Descriptions are written in the background; the caller polls the
job.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.graph_creation.describe import build_describer
from app.graph_creation.ingest import collect_uploads
from app.graph_creation.repository import SupabaseGraphRepository
from app.graph_creation.schemas import (
    DirectoryChildrenOut,
    FileContentIn,
    FileContentOut,
    FileSavedOut,
    JobOut,
    ProjectOut,
    ProjectTreeOut,
    UploadAccepted,
    UploadMode,
)
from app.graph_creation.service import GraphCreationService
from app.graph_creation.storage import SupabaseObjectStore
from app.graph_creation.tree import UploadValidationError

router = APIRouter(tags=["Graph Creation"])


def get_service() -> GraphCreationService:
    """Wire the service for a request (Supabase repository + storage + describer)."""
    settings = get_settings()
    return GraphCreationService(
        repository=SupabaseGraphRepository(),
        store=SupabaseObjectStore(bucket=settings.storage_bucket),
        describer=build_describer(settings),
        settings=settings,
    )


ServiceDep = Annotated[GraphCreationService, Depends(get_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post(
    "/uploads",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadAccepted,
    summary="Upload a markdown directory",
)
async def create_upload(
    user: UserDep,
    service: ServiceDep,
    files: Annotated[
        list[UploadFile],
        File(
            description=(
                "Markdown files whose filename carries the relative path "
                "(e.g. 'docs/api/readme.md'), or a single .zip archive."
            )
        ),
    ],
    mode: Annotated[UploadMode, Form(description="new = new tree, add = extend")] = UploadMode.NEW,
    name: Annotated[str | None, Form(description="Project name (mode=new)")] = None,
    project_id: Annotated[
        str | None, Form(description="Target project (mode=add, required)")
    ] = None,
) -> UploadAccepted:
    settings = get_settings()
    try:
        entries = await collect_uploads(
            files,
            max_files=settings.max_upload_files,
            max_file_bytes=settings.max_file_bytes,
            max_total_bytes=settings.max_upload_bytes,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    prepared = await service.prepare(
        owner_id=user.id, mode=mode, entries=entries, name=name, project_id=project_id
    )
    service.schedule(prepared)
    return UploadAccepted(
        project_id=prepared.project["id"],
        job_id=prepared.job["id"],
        mode=mode,
        total_files=prepared.tree.total_files,
    )


@router.get("/projects", response_model=list[ProjectOut], summary="List your projects")
async def list_projects(user: UserDep, service: ServiceDep) -> list[ProjectOut]:
    return [ProjectOut(**row) for row in await service.list_projects(user.id)]


@router.get("/projects/{project_id}", response_model=ProjectOut, summary="Get a project")
async def get_project(project_id: str, user: UserDep, service: ServiceDep) -> ProjectOut:
    return ProjectOut(**await service.get_project(project_id, user.id))


@router.get(
    "/projects/{project_id}/tree",
    response_model=ProjectTreeOut,
    summary="Get the project tree (with descriptions for every folder)",
)
async def get_tree(
    project_id: str,
    user: UserDep,
    service: ServiceDep,
    depth: Annotated[int | None, Query(ge=0, le=64)] = None,
) -> ProjectTreeOut:
    result = await service.get_tree(project_id, user.id, max_depth=depth)
    return ProjectTreeOut(project=result["project"], tree=result["tree"])


@router.get(
    "/directories/{directory_id}",
    response_model=DirectoryChildrenOut,
    summary="Get one directory and its immediate children",
)
async def get_directory(
    directory_id: str, user: UserDep, service: ServiceDep
) -> DirectoryChildrenOut:
    result = await service.get_directory(directory_id, user.id)
    return DirectoryChildrenOut(**result)


@router.get(
    "/files/{file_id}/content",
    response_model=FileContentOut,
    summary="Read one document's markdown",
)
async def get_file_content(file_id: str, user: UserDep, service: ServiceDep) -> FileContentOut:
    return FileContentOut(**await service.get_file_content(file_id, user.id))


@router.put(
    "/files/{file_id}/content",
    response_model=FileSavedOut,
    summary="Save one document's markdown (no model call)",
)
async def save_file_content(
    file_id: str, payload: FileContentIn, user: UserDep, service: ServiceDep
) -> FileSavedOut:
    saved = await service.save_file_content(
        file_id, user.id, text=payload.text, expected_sha256=payload.expected_sha256
    )
    return FileSavedOut(**saved)


@router.get("/jobs/{job_id}", response_model=JobOut, summary="Get the status of an upload job")
async def get_job(job_id: str, user: UserDep, service: ServiceDep) -> JobOut:
    return JobOut(**await service.get_job(job_id, user.id))
