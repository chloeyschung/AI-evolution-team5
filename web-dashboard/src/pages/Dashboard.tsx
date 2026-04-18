import { useEffect } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const contentStore = useContentStore();

  useEffect(() => {
    void Promise.all([
      contentStore.loadContent(1),
      contentStore.loadPlatforms(),
    ]);
  }, []);

  const handleDelete = async (id: number) => {
    await contentStore.deleteItem(id);
  };

  const handleSwipe = async (action: { content_id: number; action: 'keep' | 'discard' }) => {
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
      </section>
    </section>
  );
}
