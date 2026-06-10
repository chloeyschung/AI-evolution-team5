"""IOS-008: TF-IDF topic clustering with LLM Korean title generation.

Groups user content into topic clusters using TF-IDF cosine similarity (K-means).
LLM generates short Korean cluster titles from top keywords (spec §6 프롬프트 설계).
No external ML deps — TF-IDF and K-means are implemented from scratch.
"""

import json
import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from src.config import settings
from src.utils.http_client import async_client_context

logger = logging.getLogger(__name__)

_MIN_ITEMS = 4
_MAX_CLUSTERS = 7
_TITLE_TIMEOUT = 20.0

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "this", "that", "these", "those", "it", "its",
    "i", "we", "you", "he", "she", "they", "not", "no", "so", "if", "as",
    "how", "what", "when", "where", "which", "who", "why", "about", "also",
    "new", "more", "one", "can", "into", "than", "then", "there", "their",
    "s", "t", "don", "use", "using", "used", "get", "make", "like", "just",
}


@dataclass
class ClusterResult:
    title_ko: str
    keywords_en: list[str]
    content_ids: list[int] = field(default_factory=list)


# ── Input text builder (spec §6 클러스터링 알고리즘) ─────────────────────────────

def build_item_text(title: str | None, summary: str | None, keywords_en: str | None) -> str:
    """Build TF-IDF input text per spec: "{title}. {summary[:300]}. Keywords: {kws}"."""
    t = (title or "").strip()
    s = (summary or "")[:300].strip()
    k = (keywords_en or "").strip()

    parts = [t]
    if s:
        parts.append(s)
    if k:
        # keywords_en is stored as a comma-separated string from the DB
        kw_list = [w.strip() for w in k.split(",") if w.strip()]
        if kw_list:
            parts.append(f"Keywords: {', '.join(kw_list)}")
    return ". ".join(p for p in parts if p)


# ── TF-IDF helpers ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _compute_tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    df: dict[str, int] = defaultdict(int)
    for doc in docs:
        for term in set(doc):
            df[term] += 1

    vectors: list[dict[str, float]] = []
    for doc in docs:
        tf = Counter(doc)
        total = len(doc) or 1
        vec: dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((n + 1) / (df[term] + 1)) + 1.0
            vec[term] = (count / total) * idf
        vectors.append(vec)
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _kmeans(vectors: list[dict[str, float]], k: int, iterations: int = 20) -> list[int]:
    n = len(vectors)
    centroid_indices = [i * (n // k) for i in range(k)]
    centroids = [dict(vectors[i]) for i in centroid_indices]
    labels = [0] * n

    for _ in range(iterations):
        new_labels = [
            max(range(k), key=lambda ci, v=vec: _cosine(v, centroids[ci]))
            for vec in vectors
        ]
        if new_labels == labels:
            break
        labels = new_labels

        totals: list[dict[str, float]] = [{} for _ in range(k)]
        counts = [0] * k
        for idx, label in enumerate(labels):
            counts[label] += 1
            for term, val in vectors[idx].items():
                totals[label][term] = totals[label].get(term, 0.0) + val
        for ci in range(k):
            if counts[ci] > 0:
                centroids[ci] = {t: v / counts[ci] for t, v in totals[ci].items()}

    return labels


def _top_keywords(vectors: list[dict[str, float]], n: int = 5) -> list[str]:
    agg: dict[str, float] = defaultdict(float)
    for vec in vectors:
        for term, score in vec.items():
            agg[term] += score
    return [t for t, _ in sorted(agg.items(), key=lambda x: -x[1])[:n]]


# ── LLM title generation (spec §6 섹션 네이밍 설계) ──────────────────────────────

_LLM_SYSTEM = "당신은 콘텐츠 큐레이터입니다."

def _build_title_prompt(keywords: list[str], count: int) -> str:
    kw_str = ", ".join(keywords[:5])
    return (
        f"아래 키워드들로 묶인 콘텐츠 그룹의 섹션 제목을 한국어로 지어주세요.\n\n"
        f"규칙:\n"
        f"- 15자 이내\n"
        f"- 담백하고 자연스러운 문장 (과장·감탄사 금지)\n"
        f"- 키워드를 직접 나열하지 말고 주제를 함축\n"
        f"- 예시 스타일: \"AI가 바꾸는 헬스케어\", \"조용히 뜨는 기술들\", \"스타트업의 요즘 고민\"\n\n"
        f"키워드: {kw_str}\n"
        f"콘텐츠 수: {count}개\n"
        f"JSON으로만 응답: {{\"title\": \"...\"}}"
    )


async def _generate_korean_title(keywords: list[str], count: int) -> str:
    modal_tokens_ok = bool(
        getattr(settings, "MODAL_PROXY_TOKEN_ID", "") and
        getattr(settings, "MODAL_PROXY_TOKEN_SECRET", "")
    )
    extra_headers: dict = {}
    if modal_tokens_ok:
        extra_headers["Modal-Key"] = settings.MODAL_PROXY_TOKEN_ID
        extra_headers["Modal-Secret"] = settings.MODAL_PROXY_TOKEN_SECRET

    payload = {
        "model": settings.SUMMARY_MODEL,
        "messages": [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": _build_title_prompt(keywords, count)},
        ],
        "max_tokens": 40,
        "temperature": 0.4,
    }

    try:
        async with async_client_context() as client:
            resp = await client.post(
                settings.SUMMARY_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.SUMMARY_API_KEY or 'none'}",
                    **extra_headers,
                },
                timeout=_TITLE_TIMEOUT,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            # Try to parse JSON; fall back to raw text
            try:
                parsed = json.loads(raw)
                title = parsed.get("title", "").strip()
            except (json.JSONDecodeError, AttributeError):
                # LLM sometimes wraps in markdown code block
                m = re.search(r'"title"\s*:\s*"([^"]+)"', raw)
                title = m.group(1).strip() if m else raw.strip()
            return title[:15] if title else _fallback_title(keywords)
    except Exception as exc:
        logger.warning("topic title LLM failed: %s", exc)
        return _fallback_title(keywords)


def _fallback_title(keywords: list[str]) -> str:
    """Spec §6: 상위 키워드 2개를 · 로 연결."""
    parts = [k.capitalize() for k in keywords[:2] if k]
    return " · ".join(parts) if parts else "기타"


# ── Core clustering ────────────────────────────────────────────────────────────

async def cluster_user_content(items: list[tuple[int, str]]) -> list[ClusterResult]:
    """Cluster content items and generate Korean titles.

    Args:
        items: List of (server_content_id, combined_text). Use build_item_text()
               to construct the text from title/summary/keywords_en.

    Returns:
        ClusterResult list sorted by cluster size descending.
        Empty list if fewer than _MIN_ITEMS items.
    """
    if len(items) < _MIN_ITEMS:
        return []

    ids = [item[0] for item in items]
    docs = [_tokenize(item[1]) for item in items]

    valid_pairs = [(ids[i], docs[i]) for i in range(len(ids)) if docs[i]]
    if len(valid_pairs) < _MIN_ITEMS:
        return []

    valid_ids, valid_docs = zip(*valid_pairs)
    vectors = _compute_tfidf(list(valid_docs))

    k = min(_MAX_CLUSTERS, max(2, len(valid_docs) // 3))
    labels = _kmeans(vectors, k)

    clusters: dict[int, list[int]] = defaultdict(list)
    cluster_vecs: dict[int, list[dict[str, float]]] = defaultdict(list)
    for pos, label in enumerate(labels):
        clusters[label].append(valid_ids[pos])
        cluster_vecs[label].append(vectors[pos])

    results: list[ClusterResult] = []
    for label, cids in clusters.items():
        if len(cids) < 2:
            continue
        top_kws = _top_keywords(cluster_vecs[label])
        title_ko = await _generate_korean_title(top_kws, len(cids))
        results.append(ClusterResult(
            title_ko=title_ko,
            keywords_en=top_kws[:3],
            content_ids=list(cids),
        ))

    return sorted(results, key=lambda r: -len(r.content_ids))


# ── Per-user save helper (used by scheduler + on-demand trigger) ──────────────

async def cluster_and_save_for_user(user_id: int) -> int:
    """Run clustering for one user and persist results. Returns cluster count."""
    from sqlalchemy import delete as sql_delete, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from src.data.database import engine
    from src.data.models import Content, UserTopicCluster
    from src.utils.datetime_utils import utc_now

    AsyncSession_ = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSession_() as session:
        rows = await session.execute(
            select(
                Content.id,
                Content.title,
                Content.summary,
                Content.auto_tag_keywords_en,
            ).where(
                Content.user_id == user_id,
                Content.is_deleted == False,  # noqa: E712
            )
        )
        content_rows = rows.fetchall()

    if not content_rows:
        return 0

    items = [
        (cid, build_item_text(title, summary, kw_en))
        for cid, title, summary, kw_en in content_rows
    ]

    cluster_results = await cluster_user_content(items)
    if not cluster_results:
        return 0

    async with AsyncSession_() as session:
        await session.execute(
            sql_delete(UserTopicCluster).where(UserTopicCluster.user_id == user_id)
        )
        for c in cluster_results:
            session.add(UserTopicCluster(
                user_id=user_id,
                title_ko=c.title_ko,
                keywords_en=c.keywords_en,
                content_ids=c.content_ids,
                generated_at=utc_now(),
            ))
        await session.commit()

    logger.info("IOS-008 clustering: user=%d clusters=%d", user_id, len(cluster_results))
    return len(cluster_results)
