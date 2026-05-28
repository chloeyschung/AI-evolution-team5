"""Screenshot ingest endpoint — POST /api/v1/screenshot."""

import base64
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.repository import ContentRepository, IdempotencyRepository, ScreenshotImageRepository
from ...ingestion.share_processor import ImageProcessor
from ...middleware.rate_limiter import limiter
from ..dependencies import get_current_user
from ..schemas import ContentResponse, ScreenshotShareRequest, ScreenshotURLs

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/screenshot", status_code=201, response_model=ContentResponse)
@limiter.limit("10/minute")
async def upload_screenshot(
    request: Request,
    body: ScreenshotShareRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> ContentResponse:
    """Accept a base64-encoded screenshot, run OCR via Modal, store in R2, return ContentResponse."""
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": "missing_idempotency_key", "message": "Idempotency-Key header is required."})

    idempotency_repo = IdempotencyRepository(db)
    existing = await idempotency_repo.get(user_id, idempotency_key)
    if existing and existing.content_id:
        content_repo = ContentRepository(db)
        content = await content_repo.get_by_id(existing.content_id)
        if content and content.user_id == user_id:
            screenshot_repo = ScreenshotImageRepository(db)
            screenshot_map = await screenshot_repo.get_map_for_content_ids(user_id, [content.id])
            si = screenshot_map.get(content.id)
            urls = ScreenshotURLs(
                thumbnail_url=si.thumbnail_url if si else None,
                preview_url=si.preview_url if si else None,
                linked_url=getattr(content, "linked_url", None),
            ) if si else None
            return ContentResponse.from_content(content, screenshot_urls=urls)

    try:
        image_bytes = base64.b64decode(body.image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_image", "message": "image_base64 is not valid base64."}) from exc

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail={"error": "image_too_large", "message": "Image exceeds 10 MB limit."})

    share_handler = getattr(request.app.state, "share_handler", None)
    summarizer = getattr(share_handler, "_summarizer", None) if share_handler else None

    r2_client = None
    try:
        from ...storage.r2_client import R2Client
        r2_client = R2Client()
    except Exception as exc:
        logger.warning("R2Client unavailable — thumbnails will not be stored: %s", exc)

    processor = ImageProcessor(summarizer=summarizer, r2_client=r2_client)

    try:
        metadata = await processor.process_bytes(image_bytes, f"image/{body.original_format}", idempotency_key, user_id)
    except Exception as exc:
        logger.exception("Screenshot processing failed: %s", exc)
        raise HTTPException(status_code=500, detail={"error": "processing_failed", "message": "Screenshot processing failed."}) from exc

    screenshot_repo = ScreenshotImageRepository(db)
    content_repo = ContentRepository(db)

    screenshot_row = await screenshot_repo.create(
        content_id=None,  # will be updated after content is saved
        thumbnail_url=metadata.thumbnail_url,
        preview_url=getattr(metadata, "preview_url", None),
        original_key=None,
        ocr_text=getattr(metadata, "ocr_text", None),
        original_format=body.original_format,
        original_width=body.width,
        original_height=body.height,
    )

    content = await content_repo.save_screenshot(
        user_id=user_id,
        metadata=metadata,
        screenshot_image_id=screenshot_row.id,
    )

    # Back-fill content_id on screenshot row
    screenshot_row.content_id = content.id
    await db.flush()

    # Write idempotency record
    await idempotency_repo.create(user_id, idempotency_key, content.id)
    await db.commit()
    await db.refresh(content)
    await db.refresh(screenshot_row)

    urls = ScreenshotURLs(
        thumbnail_url=screenshot_row.thumbnail_url,
        preview_url=screenshot_row.preview_url,
        linked_url=getattr(content, "linked_url", None),
    )
    return ContentResponse.from_content(content, screenshot_urls=urls)
