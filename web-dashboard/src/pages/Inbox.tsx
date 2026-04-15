import { useEffect, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import styles from './Inbox.module.css';

export default function Inbox() {
  const contentStore = useContentStore();
  const [selectedPlatform, setSelectedPlatform] = useState('');

  useEffect(() => {
    contentStore.updateFilters({ status: 'inbox' });
    void contentStore.loadPlatforms();
  }, []);

  const handleSwipe = async (action: { content_id: number; action: 'keep' | 'discard' }) => {
    await contentStore.performSwipe(action);
  };

  const handleDelete = async (id: number) => {
    await contentStore.deleteItem(id);
  };

  const handlePlatformChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const platform = e.target.value || undefined;
    setSelectedPlatform(e.target.value);
    contentStore.updateFilters({ platform });
  };

  return (
    <section className={styles.page} data-testid="inbox-page">
      <header className={styles.hero}>
        <p className={styles.kicker}>Swipe Queue</p>
        <h1>One card at a time, no backlog guilt.</h1>
      </header>

      <div className={styles.filterRow}>
        <label htmlFor="platform-filter">Source</label>
        <select
          id="platform-filter"
          value={selectedPlatform}
          onChange={handlePlatformChange}
          className={styles.select}
        >
          <option value="">All platforms</option>
          {contentStore.platforms.map((platform) => (
            <option key={platform.platform} value={platform.platform}>
              {platform.platform} ({platform.count})
            </option>
          ))}
        </select>
      </div>

      {contentStore.isLoading ? <p className={styles.message}>Refreshing queue…</p> : null}

      {!contentStore.items.length && !contentStore.isLoading ? (
        <p className={styles.message}>Inbox clear. You&apos;re fully caught up.</p>
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
  );
}
