"""IOS-008: TF-IDF topic clustering with LLM Korean title generation.

Groups user content into topic clusters using TF-IDF cosine similarity (K-means).
LLM generates short Korean cluster titles from top keywords.
No external ML deps — TF-IDF and K-means are implemented from scratch.
"""

import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from src.config import settings
from src.utils.http_client import async_client_context

logger = logging.getLogger(__name__)

_MIN_ITEMS = 4       # skip clustering if user has fewer items
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
    # Spread initial centroids evenly across sorted indices
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

        # Recompute centroids as mean of assigned vectors
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


# ── LLM title generation ───────────────────────────────────────────────────────

async def _generate_korean_title(keywords: list[str]) -> str:
    modal_tokens_ok = bool(
        getattr(settings, "MODAL_PROXY_TOKEN_ID", "") and
        getattr(settings, "MODAL_PROXY_TOKEN_SECRET", "")
    )
    extra_headers: dict = {}
    if modal_tokens_ok:
        extra_headers["Modal-Key"] = settings.MODAL_PROXY_TOKEN_ID
        extra_headers["Modal-Secret"] = settings.MODAL_PROXY_TOKEN_SECRET

    kw_str = ", ".join(keywords[:5])
    prompt = (
        f"Keywords: {kw_str}\n"
        "Write a short Korean topic label (max 10 characters, noun phrase only, no punctuation)."
    )
    payload = {
        "model": settings.SUMMARY_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 30,
        "temperature": 0.3,
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
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return text[:15]
    except Exception as exc:
        logger.warning("topic title LLM failed: %s", exc)
        return keywords[0].capitalize() if keywords else "기타"


# ── Public API ─────────────────────────────────────────────────────────────────

async def cluster_user_content(items: list[tuple[int, str]]) -> list[ClusterResult]:
    """Cluster content items and generate Korean titles.

    Args:
        items: List of (server_content_id, combined_text) where
               combined_text = title + space + summary + space + keywords_en joined.

    Returns:
        ClusterResult list sorted by cluster size descending.
        Empty list if fewer than _MIN_ITEMS items.
    """
    if len(items) < _MIN_ITEMS:
        return []

    ids = [item[0] for item in items]
    docs = [_tokenize(item[1]) for item in items]

    # Filter out empty docs
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
        title_ko = await _generate_korean_title(top_kws)
        results.append(ClusterResult(
            title_ko=title_ko,
            keywords_en=top_kws[:3],
            content_ids=list(cids),
        ))

    return sorted(results, key=lambda r: -len(r.content_ids))
