import { useEffect, useMemo, useRef, useState } from 'react';
import { deleteContent, getContent, getTopicClusters, recordSwipe } from '../api/endpoints';
import ContentCard from '../components/content/ContentCard';
import ConfirmModal from '../components/ui/ConfirmModal';
import type { Content, SwipeAction, TopicCluster } from '../types';
import styles from './Dashboard.module.css';

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

interface DashboardSection {
  id: string;
  icon: string;
  title: string;
  subtitle?: string;
  items: Content[];
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [items, setItems] = useState<Content[]>([]);
  const [clusters, setClusters] = useState<TopicCluster[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [clustersLoading, setClustersLoading] = useState(true);
  const [pendingDiscard, setPendingDiscard] = useState<{ item: Content; action: SwipeAction } | null>(null);

  // ── Action strip (undo/redo) ───────────────────────────────────────────────
  const stripTimerRef = useRef<number | null>(null);
  const pendingActionRef = useRef<{
    item: Content;
    action: 'keep' | 'discard';
    index: number;
    timeoutId: number;
  } | null>(null);
  const [actionStrip, setActionStrip] = useState<{
    message: string;
    mode: 'pending' | 'undone';
    action: 'keep' | 'discard';
    item: Content;
    index: number;
  } | null>(null);

  // ── Data fetching ──────────────────────────────────────────────────────────

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    getContent(
      { status: 'inbox', platform: null, dateFrom: null, dateTo: null, category: null, hasMemo: null },
      { option: 'recency', order: 'desc' },
      1,
      200,
    )
      .then((result) => { if (!controller.signal.aborted) setItems(result.items); })
      .catch((e) => { if (!controller.signal.aborted) console.error('Dashboard: fetch failed', e); })
      .finally(() => { if (!controller.signal.aborted) setIsLoading(false); });

    return () => {
      controller.abort();
      const pending = pendingActionRef.current;
      if (pending) {
        window.clearTimeout(pending.timeoutId);
        void commitAction(pending.item, pending.action).catch(() => {});
        pendingActionRef.current = null;
      }
      if (stripTimerRef.current !== null) window.clearTimeout(stripTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setClustersLoading(true);
    getTopicClusters()
      .then((result) => { if (!controller.signal.aborted) setClusters(result); })
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setClustersLoading(false); });
    return () => controller.abort();
  }, []);

  // ── Section building ───────────────────────────────────────────────────────

  const sections = useMemo<DashboardSection[]>(() => {
    const seed = getDailySeed();
    const claimed = new Set<number>();
    const topicSections: DashboardSection[] = [];

    if (clusters.length > 0) {
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
        });
      }
    } else if (!clustersLoading) {
      const categoryGroups = new Map<string, Content[]>();
      for (const item of items) {
        if (!item.auto_tag_category || claimed.has(item.id)) continue;
        const existing = categoryGroups.get(item.auto_tag_category) ?? [];
        existing.push(item);
        categoryGroups.set(item.auto_tag_category, existing);
      }
      for (const [cat, catItems] of categoryGroups.entries()) {
        catItems.forEach((i) => claimed.add(i.id));
        const uniqueKeywords = Array.from(new Set(catItems.flatMap((i) => i.auto_tag_keywords_en))).slice(0, 3);
        topicSections.push({
          id: `topic-category-${cat}`,
          icon: '📚',
          title: CATEGORY_LABELS[cat] ?? cat,
          subtitle: uniqueKeywords.join(' · ') || undefined,
          items: catItems,
        });
      }
    }

    const dateBuckets = new Map<string, Content[]>();
    for (const item of items) {
      if (claimed.has(item.id)) continue;
      const bucket = getDateBucket(item.created_at);
      const existing = dateBuckets.get(bucket) ?? [];
      existing.push(item);
      dateBuckets.set(bucket, existing);
    }
    // Separate today's section (always pinned to top) from the rest
    const todayItems = dateBuckets.get('today') ?? [];
    if (todayItems.length > 0) todayItems.forEach((i) => claimed.add(i.id));

    const dateSections: DashboardSection[] = DATE_BUCKET_ORDER
      .filter((bucket) => bucket !== 'today' && (dateBuckets.get(bucket)?.length ?? 0) > 0)
      .map((bucket) => {
        const bucketItems = dateBuckets.get(bucket)!;
        bucketItems.forEach((i) => claimed.add(i.id));
        return { id: `date-${bucket}`, icon: '📅', title: DATE_BUCKET_LABELS[bucket], items: bucketItems };
      });

    const domainGroups = new Map<string, Content[]>();
    for (const item of items) {
      if (claimed.has(item.id)) continue;
      const domain = normalizeDomain(item.url);
      const existing = domainGroups.get(domain) ?? [];
      existing.push(item);
      domainGroups.set(domain, existing);
    }
    const sourceSections: DashboardSection[] = Array.from(domainGroups.entries())
      .sort((a, b) => b[1].length - a[1].length)
      .slice(0, 8)
      .map(([domain, domainItems]) => ({ id: `source-${domain}`, icon: '🌐', title: getDomainDisplay(domain), items: domainItems }));

    const todaySection: DashboardSection[] = todayItems.length > 0
      ? [{ id: 'date-today', icon: '📅', title: DATE_BUCKET_LABELS['today'], items: todayItems }]
      : [];

    // Order: 오늘 → topic/category → date + source (shuffled daily)
    return [...todaySection, ...topicSections, ...seededShuffle([...dateSections, ...sourceSections], seed)];
  }, [items, clusters, clustersLoading]);

  // ── Keep / Discard logic (mirrors original Dashboard) ─────────────────────

  const removeLocalItem = (id: number) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const insertLocalItem = (item: Content, index: number) => {
    setItems((prev) => {
      const next = [...prev];
      next.splice(Math.max(0, Math.min(index, next.length)), 0, item);
      return next;
    });
  };

  const commitAction = async (item: Content, action: 'keep' | 'discard') => {
    if (action === 'keep') {
      await recordSwipe({ content_id: item.id, action: 'keep' });
    } else {
      await deleteContent(item.id);
    }
  };

  const scheduleCommit = (item: Content, action: 'keep' | 'discard', index: number) => {
    if (stripTimerRef.current !== null) { window.clearTimeout(stripTimerRef.current); stripTimerRef.current = null; }
    const timeoutId = window.setTimeout(async () => {
      try { await commitAction(item, action); }
      catch { insertLocalItem(item, index); }
      finally { pendingActionRef.current = null; setActionStrip(null); }
    }, 3200);
    pendingActionRef.current = { item, action, index, timeoutId };
    setActionStrip({ message: action === 'keep' ? 'Item archived.' : 'Item discarded.', mode: 'pending', action, item, index });
  };

  const queueAction = (item: Content, action: 'keep' | 'discard') => {
    const current = pendingActionRef.current;
    if (current) { window.clearTimeout(current.timeoutId); void commitAction(current.item, current.action).catch(() => {}); pendingActionRef.current = null; }
    const idx = items.findIndex((c) => c.id === item.id);
    removeLocalItem(item.id);
    scheduleCommit(item, action, idx === -1 ? 0 : idx);
  };

  const handleDelete = (id: number) => {
    const item = items.find((c) => c.id === id);
    if (!item) return;
    setPendingDiscard({ item, action: { content_id: id, action: 'discard' } });
  };

  const handleSwipe = (action: SwipeAction) => {
    const item = items.find((c) => c.id === action.content_id);
    if (!item) return;
    if (action.action === 'discard') { setPendingDiscard({ item, action }); return; }
    queueAction(item, 'keep');
  };

  const handleConfirmDiscard = () => {
    if (!pendingDiscard) return;
    queueAction(pendingDiscard.item, 'discard');
    setPendingDiscard(null);
  };

  const handleUndoAction = () => {
    const pending = pendingActionRef.current;
    if (!pending) return;
    window.clearTimeout(pending.timeoutId);
    insertLocalItem(pending.item, pending.index);
    pendingActionRef.current = null;
    setActionStrip({ message: 'Action undone.', mode: 'undone', action: pending.action, item: pending.item, index: pending.index });
    if (stripTimerRef.current !== null) window.clearTimeout(stripTimerRef.current);
    stripTimerRef.current = window.setTimeout(() => { setActionStrip(null); stripTimerRef.current = null; }, 2200);
  };

  const handleRedoAction = () => {
    if (!actionStrip || actionStrip.mode !== 'undone') return;
    removeLocalItem(actionStrip.item.id);
    scheduleCommit(actionStrip.item, actionStrip.action, actionStrip.index);
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <ConfirmModal
        isOpen={pendingDiscard !== null}
        message="Discard this item?"
        onConfirm={handleConfirmDiscard}
        onCancel={() => setPendingDiscard(null)}
      />

      <section className={styles.page} data-testid="dashboard-page">
        <header className={styles.heroPlane} data-testid="dashboard-hero-plane">
          <p className={styles.kicker}>TODAY&apos;S READING FLOW</p>
          <h1>Process pending items with less context switching.</h1>
          <p className={styles.description}>
            Handle your queue in short, focused passes. Start with one item and keep momentum without reopening context.
          </p>
        </header>

        {actionStrip ? (
          <div className={styles.actionStrip} role="status" aria-live="polite">
            <span>{actionStrip.message}</span>
            <div className={styles.actionStripButtons}>
              {actionStrip.mode === 'pending' ? (
                <button type="button" className={styles.actionStripBtn} onClick={handleUndoAction}>Undo</button>
              ) : (
                <button type="button" className={styles.actionStripBtn} onClick={handleRedoAction}>Redo</button>
              )}
            </div>
          </div>
        ) : null}

        {isLoading ? (
          <p className={styles.message}>콘텐츠를 불러오는 중…</p>
        ) : items.length === 0 ? (
          <p className={styles.message}>
            Nothing queued yet. Save one article from the extension and it will show up here.
          </p>
        ) : (
          <div className={styles.sections}>
            {clustersLoading && (
              <div className={styles.clusterHint}>📚 주제 분석 중…</div>
            )}
            {sections.map((section) => (
              <section key={section.id} className={styles.section}>
                <div className={styles.sectionHeader}>
                  <div className={styles.sectionTitleRow}>
                    <span className={styles.sectionIcon} aria-hidden="true">{section.icon}</span>
                    <h2 className={styles.sectionTitle}>{section.title}</h2>
                    <span className={styles.sectionCount}>{section.items.length}</span>
                  </div>
                  {section.subtitle && (
                    <div className={styles.keywordChips}>
                      {section.subtitle.split(' · ').map((kw) => (
                        <span key={kw} className={styles.chip}>{kw}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className={styles.carousel}>
                  {section.items.map((item) => (
                    <div key={item.id} className={styles.carouselItem}>
                      <ContentCard
                        content={item}
                        onDelete={handleDelete}
                        onSwipe={handleSwipe}
                      />
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
