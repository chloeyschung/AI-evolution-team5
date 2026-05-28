"""Source Insights endpoints — GET/POST /api/v1/sources."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.models import Content
from ...data.repository import SourceInsightsRepository, TrustedSourceRepository
from ...middleware.rate_limiter import limiter
from ...utils.datetime_utils import serialize_datetime, utc_now
from ..dependencies import get_current_user
from ..schemas import (
    SourceConfirmRequest,
    SourceInsight,
    SourceNarrativeResponse,
    SourcesListResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/sources", response_model=SourcesListResponse)
async def list_sources(
    min_saves: int = 5,
    min_keep_rate: float = 0.70,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourcesListResponse:
    """Return the user's behavioral trust map (inferred + manually added sources)."""
    stats_repo = SourceInsightsRepository(db)
    trusted_repo = TrustedSourceRepository(db)

    inferred = await stats_repo.get_source_stats(user_id, min_saves=min_saves, min_keep_rate=min_keep_rate)
    inferred_domains = {s["domain"] for s in inferred}

    manual_rows = await trusted_repo.get_all(user_id)
    manual_only = [r for r in manual_rows if r.domain not in inferred_domains]

    sources: list[SourceInsight] = []
    for s in inferred:
        trusted = next((r for r in manual_rows if r.domain == s["domain"]), None)
        sources.append(
            SourceInsight(
                domain=s["domain"],
                favicon_url=f"https://{s['domain']}/favicon.ico",
                display_name=trusted.display_name if trusted else None,
                save_count=s["save_count"],
                keep_count=s["keep_count"],
                keep_rate=s["keep_rate"],
                manually_added=trusted.manually_added if trusted else False,
                most_recent_title=s["most_recent_title"],
            )
        )
    for row in manual_only:
        sources.append(
            SourceInsight(
                domain=row.domain,
                favicon_url=f"https://{row.domain}/favicon.ico",
                display_name=row.display_name,
                save_count=0,
                keep_count=0,
                keep_rate=0.0,
                manually_added=True,
                most_recent_title=None,
            )
        )
    return SourcesListResponse(sources=sources)


@router.post("/sources/{domain}/confirm", response_model=SourceInsight)
async def confirm_source(
    domain: str,
    body: SourceConfirmRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceInsight:
    trusted_repo = TrustedSourceRepository(db)
    trigger_id = body.trigger_content_id

    if trigger_id is None:
        now = utc_now()
        trigger_id = await trusted_repo.find_trigger_content(user_id, domain, now, body.user_timezone)

    row = await trusted_repo.upsert(
        user_id=user_id,
        domain=domain,
        manually_added=True,
        trigger_content_id=trigger_id,
        display_name=body.display_name,
    )
    await db.commit()
    await db.refresh(row)

    return SourceInsight(
        domain=row.domain,
        favicon_url=f"https://{row.domain}/favicon.ico",
        display_name=row.display_name,
        save_count=0,
        keep_count=0,
        keep_rate=0.0,
        manually_added=True,
        most_recent_title=None,
    )


@router.get("/sources/{domain}/narrative", response_model=SourceNarrativeResponse)
@limiter.limit("20/minute")
async def get_source_narrative(
    request: Request,
    domain: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceNarrativeResponse:
    """Return (or generate) the LLM narrative for a trusted source."""
    trusted_repo = TrustedSourceRepository(db)
    stats_repo = SourceInsightsRepository(db)

    row = await trusted_repo.get_by_domain(user_id, domain)
    if row is None:
        row = await trusted_repo.upsert(user_id=user_id, domain=domain)
        await db.flush()

    if trusted_repo.is_narrative_fresh(row):
        return SourceNarrativeResponse(
            text=row.narrative_cached or "",
            generated_at=serialize_datetime(row.narrative_generated_at) if row.narrative_generated_at else None,
        )

    # Fetch stats for narrative context
    all_stats = await stats_repo.get_source_stats(user_id, min_saves=1, min_keep_rate=0.0)
    domain_stat = next((s for s in all_stats if s["domain"] == domain), None)
    kept_titles = [domain_stat["most_recent_title"]] if domain_stat and domain_stat["most_recent_title"] else []

    manual_context: str | None = None
    if row.manually_added and row.trigger_content_id is not None:
        content_result = await db.execute(select(Content.title, Content.created_at).where(Content.id == row.trigger_content_id))
        trigger = content_result.fetchone()
        if trigger and trigger[0]:
            added_str = row.added_at.strftime("%Y-%m-%d") if row.added_at else "unknown date"
            manual_context = f"You added this source on {added_str} after reading '{trigger[0]}'."

    share_handler = getattr(request.app.state, "share_handler", None)
    summarizer = getattr(share_handler, "_summarizer", None) if share_handler else None

    if summarizer is None:
        text = ""
    else:
        try:
            text = await summarizer.generate_source_narrative(
                source_name=domain,
                kept_titles=kept_titles,
                topics=[],
                manual_context=manual_context,
            )
        except Exception as exc:
            logger.warning("Narrative generation failed for %s: %s", domain, exc)
            text = ""

    await trusted_repo.update_narrative(user_id, domain, text)
    await db.commit()
    await db.refresh(row)

    return SourceNarrativeResponse(
        text=text,
        generated_at=serialize_datetime(row.narrative_generated_at) if row.narrative_generated_at else None,
    )
