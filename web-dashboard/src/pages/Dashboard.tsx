import { useEffect, useRef, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import ContentTable from '../components/content/ContentTable';
import type { Content, SwipeAction, ViewMode } from '../types';
import { DEFAULT_SETTINGS } from '../types';
import { deleteContent, recordSwipe } from '../api/endpoints';
import styles from './Dashboard.module.css';

function loadDefaultView(): ViewMode {
  try {
    const raw = localStorage.getItem('briefly_settings');
    if (raw) return (JSON.parse(raw).defaultView as ViewMode) || DEFAULT_SETTINGS.defaultView;
  } catch {
    // ignore
  }
  return DEFAULT_SETTINGS.defaultView;
}

export default function Dashboard() {
  const contentStore = useContentStore();
  const [viewMode] = useState<ViewMode>(loadDefaultView);
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

  useEffect(() => {
    contentStore.updateFilters({ status: 'inbox' });
    void contentStore.loadPlatforms();
    return () => {
      const pending = pendingActionRef.current;
      if (pending) {
        window.clearTimeout(pending.timeoutId);
        // Ensure pending action is persisted even if user navigates away before delay.
        void commitAction(pending.item, pending.action).catch(() => {});
        pendingActionRef.current = null;
      }
      if (stripTimerRef.current !== null) {
        window.clearTimeout(stripTimerRef.current);
      }
      contentStore.updateFilters({ status: 'all' });
    };
  }, []);

  const removeLocalItem = (id: number) => {
    useContentStore.setState((state) => ({
      items: state.items.filter((item) => item.id !== id),
      selectedIds: new Set(Array.from(state.selectedIds).filter((selectedId) => selectedId !== id)),
    }));
  };

  const insertLocalItem = (item: Content, index: number) => {
    useContentStore.setState((state) => {
      const nextItems = [...state.items];
      const targetIndex = Math.max(0, Math.min(index, nextItems.length));
      nextItems.splice(targetIndex, 0, item);
      return { items: nextItems };
    });
  };

  const commitAction = async (item: Content, action: 'keep' | 'discard') => {
    if (action === 'keep') {
      await recordSwipe({ content_id: item.id, action: 'keep' });
      return;
    }
    await deleteContent(item.id);
  };

  const scheduleCommit = (item: Content, action: 'keep' | 'discard', index: number) => {
    if (stripTimerRef.current !== null) {
      window.clearTimeout(stripTimerRef.current);
      stripTimerRef.current = null;
    }
    const timeoutId = window.setTimeout(async () => {
      try {
        await commitAction(item, action);
      } catch {
        insertLocalItem(item, index);
      } finally {
        pendingActionRef.current = null;
        setActionStrip(null);
      }
    }, 3200);
    pendingActionRef.current = { item, action, index, timeoutId };
    setActionStrip({
      message: action === 'keep' ? 'Moved to archived.' : 'Moved to trash.',
      mode: 'pending',
      action,
      item,
      index,
    });
  };

  const queueAction = (item: Content, action: 'keep' | 'discard') => {
    const currentPending = pendingActionRef.current;
    if (currentPending) {
      window.clearTimeout(currentPending.timeoutId);
      void commitAction(currentPending.item, currentPending.action).catch(() => {});
      pendingActionRef.current = null;
    }

    const currentItems = useContentStore.getState().items;
    const currentIndex = currentItems.findIndex((candidate) => candidate.id === item.id);
    removeLocalItem(item.id);
    scheduleCommit(item, action, currentIndex === -1 ? 0 : currentIndex);
  };

  const handleDelete = async (id: number) => {
    const item = useContentStore.getState().items.find((candidate) => candidate.id === id);
    if (!item) return;
    queueAction(item, 'discard');
  };

  const handleSwipe = async (action: SwipeAction) => {
    const item = useContentStore.getState().items.find((candidate) => candidate.id === action.content_id);
    if (!item) return;
    queueAction(item, action.action);
  };

  const handleUndoAction = () => {
    const pending = pendingActionRef.current;
    if (!pending) return;
    window.clearTimeout(pending.timeoutId);
    insertLocalItem(pending.item, pending.index);
    pendingActionRef.current = null;
    setActionStrip({
      message: 'Action undone.',
      mode: 'undone',
      action: pending.action,
      item: pending.item,
      index: pending.index,
    });
    if (stripTimerRef.current !== null) {
      window.clearTimeout(stripTimerRef.current);
    }
    stripTimerRef.current = window.setTimeout(() => {
      setActionStrip(null);
      stripTimerRef.current = null;
    }, 2200);
  };

  const handleRedoAction = () => {
    if (!actionStrip || actionStrip.mode !== 'undone') return;
    removeLocalItem(actionStrip.item.id);
    scheduleCommit(actionStrip.item, actionStrip.action, actionStrip.index);
  };

  return (
    <section className={styles.page} data-testid="dashboard-page">
      <header className={styles.heroPlane} data-testid="dashboard-hero-plane">
        <p className={styles.kicker}>TODAY&apos;S READING FLOW</p>
        <h1>Process pending items with less context switching.</h1>
        <p className={styles.description}>
          Handle your queue in short, focused passes. Start with one item and keep momentum without reopening context.
        </p>
      </header>

      <section className={styles.workLane} data-testid="dashboard-work-lane">
        {actionStrip ? (
          <div className={styles.actionStrip} role="status" aria-live="polite">
            <span>{actionStrip.message}</span>
            <div className={styles.actionStripButtons}>
              {actionStrip.mode === 'pending' ? (
                <button type="button" className={styles.actionStripBtn} onClick={handleUndoAction}>
                  Undo
                </button>
              ) : (
                <button type="button" className={styles.actionStripBtn} onClick={handleRedoAction}>
                  Redo
                </button>
              )}
            </div>
          </div>
        ) : null}

        {contentStore.isLoading ? <p className={styles.message}>Loading your stack…</p> : null}

        {!contentStore.items.length && !contentStore.isLoading ? (
          <p className={styles.message}>
            Nothing queued yet. Save one article from the extension and it will show up here.
          </p>
        ) : null}

        {viewMode === 'list' ? (
          <ContentTable
            items={contentStore.items}
            onOpen={() => {}}
            onDelete={handleDelete}
            onSwipe={handleSwipe}
            keepActionLabel="Keep"
            keepActionTone="signal"
            keepActionIcon="archive"
            emptyMessage=""
          />
        ) : (
          <div className={styles.grid}>
            {contentStore.items.map((item) => (
              <ContentCard
                key={item.id}
                content={item}
                onDelete={handleDelete}
                onSwipe={handleSwipe}
              />
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
