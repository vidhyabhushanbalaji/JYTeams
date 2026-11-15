"""HTTP routes for the Chat section.

Mounted at ``/api/chat``. A project's group chat needs no creation step: the project is the
channel, so ``GET /channels`` is "my projects, with the last thing said in each".

The desktop app polls ``GET /projects/{id}/messages?after_seq=`` (a monotonic cursor) rather than
holding a socket open: the renderer never touches the network, and one small read per few seconds
is cheaper to own than a WebSocket bridge through the Electron main process.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.chat.adapters import MentionCatalogueAdapter
from app.chat.repository import SupabaseChatRepository
from app.chat.schemas import ChannelOut, ChatMessageOut, MentionTargetOut, MessageIn
from app.chat.service import DEFAULT_LIMIT, MAX_LIMIT, MAX_TARGETS, ChatService
from app.core.access import SupabaseProjectAccess
from app.core.auth import CurrentUser, get_current_user

router = APIRouter(tags=["Chat"])


def get_service() -> ChatService:
    """Wire the service (Supabase messages, membership, the mention catalogue)."""
    return ChatService(
        repository=SupabaseChatRepository(),
        access=SupabaseProjectAccess(),
        catalogue=MentionCatalogueAdapter(),
    )


ServiceDep = Annotated[ChatService, Depends(get_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/channels", response_model=list[ChannelOut], summary="My project chats")
async def channels(user: UserDep, service: ServiceDep) -> list[ChannelOut]:
    return [ChannelOut(**row) for row in await service.channels(user.id)]


@router.get(
    "/projects/{project_id}/messages",
    response_model=list[ChatMessageOut],
    summary="A project's messages (or everything after a cursor)",
)
async def messages(
    project_id: str,
    user: UserDep,
    service: ServiceDep,
    after_seq: Annotated[
        int | None, Query(ge=0, description="Only messages newer than this seq (the poll)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> list[ChatMessageOut]:
    rows = await service.messages(
        member_id=user.id, project_id=project_id, after_seq=after_seq, limit=limit
    )
    return [ChatMessageOut(**row) for row in rows]


@router.post(
    "/projects/{project_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatMessageOut,
    summary="Post a message (mentions are resolved and validated here)",
)
async def post_message(
    project_id: str, payload: MessageIn, user: UserDep, service: ServiceDep
) -> ChatMessageOut:
    return ChatMessageOut(
        **await service.post_message(member_id=user.id, project_id=project_id, body=payload.body)
    )


@router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a message (author, or the project owner)",
)
async def delete_message(message_id: str, user: UserDep, service: ServiceDep) -> Response:
    await service.delete_message(member_id=user.id, message_id=message_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/projects/{project_id}/mention-targets",
    response_model=list[MentionTargetOut],
    summary="Documents, folders, tickets and calendar events the composer may offer after an @",
)
async def mention_targets(
    project_id: str,
    user: UserDep,
    service: ServiceDep,
    q: Annotated[str, Query(max_length=120, description="What was typed after the @")] = "",
    limit: Annotated[int, Query(ge=1, le=MAX_TARGETS)] = MAX_TARGETS,
) -> list[MentionTargetOut]:
    rows = await service.mention_targets(
        member_id=user.id, project_id=project_id, query=q, limit=limit
    )
    return [MentionTargetOut(**row) for row in rows]
