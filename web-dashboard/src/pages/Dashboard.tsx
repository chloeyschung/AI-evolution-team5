import { useEffect, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import ContentTable from '../components/content/ContentTable';
import type { SwipeAction, ViewMode } from '../types';
import { DEFAULT_SETTINGS } from '../types';
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

  useEffect(() => {
    void Promise.all([
      contentStore.loadContent(1),
      contentStore.loadPlatforms(),
    ]);
  }, []);

  const handleDelete = async (id: number) => {
    await contentStore.deleteItem(id);
  };

  const handleSwipe = async (action: SwipeAction) => {
    await contentStore.performSwipe(action);
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
