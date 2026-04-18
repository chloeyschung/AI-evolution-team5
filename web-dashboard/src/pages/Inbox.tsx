import { useEffect, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentDrawer from '../components/content/ContentDrawer';
import ContentTable from '../components/content/ContentTable';
import styles from './Inbox.module.css';

export default function Inbox() {
  const contentStore = useContentStore();
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [selectedContentId, setSelectedContentId] = useState<number | null>(null);

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
        <h1>Inbox</h1>
        <p className={styles.subtitle}>Items requiring action</p>
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

      <ContentTable
        items={contentStore.items}
        onOpen={setSelectedContentId}
        onDelete={handleDelete}
        onSwipe={handleSwipe}
        emptyMessage="No inbox items requiring action."
      />

      <ContentDrawer
        contentId={selectedContentId}
        onClose={() => setSelectedContentId(null)}
      />
    </section>
  );
}
