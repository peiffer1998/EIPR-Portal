"""Storage and object usage endpoints."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import S3Client
from app.models.document import Document
from app.models.user import User, UserRole

router = APIRouter(prefix="/storage", tags=["storage"])


class StorageBreakdown(BaseModel):
    count: int
    bytes: int


class StorageUsageResponse(BaseModel):
    total_original_bytes: int
    total_web_bytes: int
    total_count: int
    by_type: dict[str, StorageBreakdown]


def _increment(bucket: dict[str, list[int]], key: str, size: int) -> None:
    if size < 0:
        return
    bucket[key].append(size)


@router.get(
    "/usage",
    response_model=StorageUsageResponse,
    summary="Summarise stored media usage",
)
async def storage_usage(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    s3_client: Annotated[S3Client, Depends(deps.get_s3_client)],
) -> StorageUsageResponse:
    if current_user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    result = await session.execute(
        select(Document).where(Document.account_id == current_user.account_id)
    )
    documents = list(result.scalars().unique().all())

    originals = 0
    web_total = 0
    grouped: dict[str, list[int]] = defaultdict(list)

    for document in documents:
        if document.object_key:
            meta = s3_client.get_object_metadata(document.object_key)
            size = meta.size if meta else 0
            originals += size
            _increment(
                grouped, document.content_type or "application/octet-stream", size
            )
        if document.object_key_web:
            meta_web = s3_client.get_object_metadata(document.object_key_web)
            size_web = meta_web.size if meta_web else (document.bytes_web or 0)
            web_total += size_web
            web_type = document.content_type_web or "image/webp"
            _increment(grouped, web_type, size_web)

    breakdown = {
        key: StorageBreakdown(count=len(values), bytes=sum(values))
        for key, values in grouped.items()
    }

    return StorageUsageResponse(
        total_original_bytes=originals,
        total_web_bytes=web_total,
        total_count=len(documents),
        by_type=breakdown,
    )
