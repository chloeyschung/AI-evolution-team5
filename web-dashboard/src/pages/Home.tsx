import { useEffect, useMemo, useState } from 'react';
import { getContent, getTopicClusters } from '../api/endpoints';
import ContentCarouselCard from '../components/content/ContentCarouselCard';
import type { Content, TopicCluster } from '../types';
import styles from './Home.module.css';

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  Tech: '기술',
  Business: '비즈니스',
  Essays: '에세이',
  Research: '연구',
  Lifestyle: '라이프스타일',
  News: '뉴스',
  Culture: '문화',
  Other: '기타',
};

const DATE_BUCKET_LABELS: Record<string, string> = {
  today: '오늘 저장한 따끈따끈한 글',
  thisWeek: '이번주에 발견한 좋은 글',
  lastWeek: '놓치지 마세요! 지난주에 담아둔',
  thisMonth: '이번 달의 링크들',
  lastMonth: '한달전의 내가 저장한 글',
  older: '오랜만에 꺼내 읽어 볼까요?',
};

const DATE_BUCKET_ORDER = ['today', 'thisWeek', 'lastWeek', 'thisMonth', 'lastMonth', 'older'] as const;

const DOMAIN_BRAND_MAP: Record<string, string> = {
  'youtube.com': 'YouTube',
  'linkedin.com': 'LinkedIn',
  'medium.com': 'Medium',
  'twitter.com': 'X',
  'x.com': 'X',
  'reddit.com': 'Reddit',
  'github.com': 'GitHub',
  'naver.com': 'Naver',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function normalizeDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function getDomainDisplay(domain: string): string {
  return DOMAIN_BRAND_MAP[domain] ?? domain;
}

function getDateBucket(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  // Monday of current week
  const dayOfWeek = now.getDay();
  const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  const thisWeekMonday = new Date(todayStart);
  thisWeekMonday.setDate(todayStart.getDate() - daysToMonday);

  const lastWeekMonday = new Date(thisWeekMonday);
  lastWeekMonday.setDate(thisWeekMonday.getDate() - 7);

  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);

  if (date >= todayStart) return 'today';
  if (date >= thisWeekMonday) return 'thisWeek';
  if (date >= lastWeekMonday) return 'lastWeek';
  if (date >= thisMonthStart) return 'thisMonth';
  if (date >= lastMonthStart) return 'lastMonth';
  return 'older';
}

// Seeded Fisher-Yates shuffle for stable daily ordering
function seededShuffle<T>(arr: T[], seed: number): T[] {
  const result = [...arr];
  let s = seed;
  for (let i = result.length - 1; i > 0; i--) {
    s = ((s * 1664525) + 1013904223) | 0;
    const j = Math.abs(s) % (i + 1);
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function getDailySeed(): number {
  const d = new Date();
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
}

// ─── Section Type ─────────────────────────────────────────────────────────────

interface HomeSection {
  id: string;
  icon: string;
  title: string;
  subtitle?: string;
  items: Content[];
  pinned?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Home() {
  const [items, setItems] = useState<Content[]>([]);
  const [clusters, setClusters] = useState<TopicCluster[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [clustersLoading, setClustersLoading] = useState(true);

  // IOS-006 + IOS-007: fetch all saved content
  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    getContent(
      { status: 'all', platform: null, dateFrom: null, dateTo: null, category: null, hasMemo: null },
      { option: 'recency', order: 'desc' },
      1,
      200,
    )
      .then((result) => {
        if (!controller.signal.aborted) setItems(result.items);
      })
      .catch((e) => {
        if (!controller.signal.aborted) console.error('Home: content fetch failed', e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
    return () => controller.abort();
  }, []);

  // IOS-008: fetch dynamic topic clusters
  useEffect(() => {
    const controller = new AbortController();
    setClustersLoading(true);
    getTopicClusters()
      .then((result) => {
        if (!controller.signal.aborted) setClusters(result);
      })
      .catch(() => {
        // silently fall back to auto_tag_category grouping
      })
      .finally(() => {
        if (!controller.signal.aborted) setClustersLoading(false);
      });
    return () => controller.abort();
  }, []);

  const sections = useMemo<HomeSection[]>(() => {
    const seed = getDailySeed();
    // Track claimed IDs so each item appears in exactly one section.
    // Priority: topic/category → date → source
    const claimed = new Set<number>();

    // ── Topic sections (pinned — always first) ──────────────────────────────
    const topicSections: HomeSection[] = [];

    if (clusters.length > 0) {
      // IOS-008: dynamic clusters from GET /api/v1/topics
      const contentById = new Map(items.map((item) => [item.id, item]));
      for (const cluster of clusters) {
        const clusterItems = cluster.content_ids
          .map((id) => contentById.get(id))
          .filter((item): item is Content => item !== undefined && !claimed.has(item.id));
        if (clusterItems.length === 0) continue;
        clusterItems.forEach((i) => claimed.add(i.id));
        topicSections.push({
          id: `topic-cluster-${cluster.id}`,
          icon: '📚',
          title: cluster.title_ko,
          subtitle: cluster.keywords_en.slice(0, 3).join(' · ') || undefined,
          items: clusterItems,
          pinned: true,
        });
      }
    } else if (!clustersLoading) {
      // IOS-006 fallback: group by auto_tag_category
      const categoryGroups = new Map<string, Content[]>();
      for (const item of items) {
        if (!item.auto_tag_category || claimed.has(item.id)) continue;
        const existing = categoryGroups.get(item.auto_tag_category) ?? [];
        existing.push(item);
        categoryGroups.set(item.auto_tag_category, existing);
      }
      for (const [cat, catItems] of categoryGroups.entries()) {
        catItems.forEach((i) => claimed.add(i.id));
        const uniqueKeywords = Array.from(
          new Set(catItems.flatMap((i) => i.auto_tag_keywords_en)),
        ).slice(0, 3);
        topicSections.push({
          id: `topic-category-${cat}`,
          icon: '📚',
          title: CATEGORY_LABELS[cat] ?? cat,
          subtitle: uniqueKeywords.join(' · ') || undefined,
          items: catItems,
          pinned: true,
        });
      }
    }

    // ── Date sections (unclaimed items only) ────────────────────────────────
    const dateBuckets = new Map<string, Content[]>();
    for (const item of items) {
      if (claimed.has(item.id)) continue;
      const bucket = getDateBucket(item.created_at);
      const existing = dateBuckets.get(bucket) ?? [];
      existing.push(item);
      dateBuckets.set(bucket, existing);
    }
    const dateSections: HomeSection[] = DATE_BUCKET_ORDER
      .filter((bucket) => (dateBuckets.get(bucket)?.length ?? 0) > 0)
      .map((bucket) => {
        const bucketItems = dateBuckets.get(bucket)!;
        bucketItems.forEach((i) => claimed.add(i.id));
        return {
          id: `date-${bucket}`,
          icon: '📅',
          title: DATE_BUCKET_LABELS[bucket],
          items: bucketItems,
        };
      });

    // ── Source sections (unclaimed items only, max 8) ───────────────────────
    const domainGroups = new Map<string, Content[]>();
    for (const item of items) {
      if (claimed.has(item.id)) continue;
      const domain = normalizeDomain(item.url);
      const existing = domainGroups.get(domain) ?? [];
      existing.push(item);
      domainGroups.set(domain, existing);
    }
    const sourceSections: HomeSection[] = Array.from(domainGroups.entries())
      .sort((a, b) => b[1].length - a[1].length)
      .slice(0, 8)
      .map(([domain, domainItems]) => ({
        id: `source-${domain}`,
        icon: '🌐',
        title: getDomainDisplay(domain),
        items: domainItems,
      }));

    // Topic sections pinned first; date + source shuffled daily
    const shuffled = seededShuffle([...dateSections, ...sourceSections], seed);
    return [...topicSections, ...shuffled];
  }, [items, clusters, clustersLoading]);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>홈</h1>
        </header>
        <p className={styles.message}>콘텐츠를 불러오는 중…</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>홈</h1>
          <p className={styles.subtitle}>저장한 콘텐츠를 주제 · 날짜 · 출처별로 둘러보세요</p>
        </header>
        <p className={styles.message}>
          아직 저장된 콘텐츠가 없어요. 익스텐션으로 링크를 저장해보세요.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>홈</h1>
        <p className={styles.subtitle}>저장한 콘텐츠를 주제 · 날짜 · 출처별로 둘러보세요</p>
      </header>

      {clustersLoading && (
        <div className={styles.clusterHint}>📚 주제 분석 중…</div>
      )}

      <div className={styles.sections}>
        {sections.map((section) => (
          <section key={section.id} className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitleRow}>
                <span className={styles.sectionIcon} aria-hidden="true">
                  {section.icon}
                </span>
                <h2 className={styles.sectionTitle}>{section.title}</h2>
                <span className={styles.sectionCount}>{section.items.length}</span>
              </div>
              {section.subtitle && (
                <div className={styles.keywordChips}>
                  {section.subtitle.split(' · ').map((kw) => (
                    <span key={kw} className={styles.chip}>
                      {kw}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className={styles.carousel}>
              {section.items.map((item) => (
                <ContentCarouselCard key={item.id} content={item} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
