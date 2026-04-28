import { useEffect, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentDrawer from '../components/content/ContentDrawer';
import ContentTable from '../components/content/ContentTable';
import { removeDuplicates } from '../api/endpoints';
import styles from './Inbox.module.css';

export default function Inbox() {
  const contentStore = useContentStore();
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [selectedContentId, setSelectedContentId] = useState<number | null>(null);
  const [isRemovingDuplicates, setIsRemovingDuplicates] = useState(false);

  useEffect(() => {
    contentStore.updateFilters({ status: 'all' });
    void contentStore.loadPlatforms();
    return () => {
      contentStore.updateFilters({ platform: null });
    };
  }, []);

  const handleDelete = async (id: number) => {
    await contentStore.deleteItem(id);
  };

  const handleKeep = async (id: number) => {
    await contentStore.performSwipe({ content_id: id, action: 'keep' });
  };

  const handlePlatformChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const platform = e.target.value || undefined;
    setSelectedPlatform(e.target.value);
    contentStore.updateFilters({ platform });
  };

  const handleSortChange = (option: 'recency' | 'platform' | 'title' | 'status') => {
    const nextOrder =
      contentStore.sort.option === option
        ? (contentStore.sort.order === 'asc' ? 'desc' : 'asc')
        : 'asc';
    contentStore.updateSort({ option, order: nextOrder });
  };

  const handleRemoveDuplicates = async () => {
    setIsRemovingDuplicates(true);
    try {
      await removeDuplicates();
      await contentStore.loadContent(1);
      await contentStore.loadPlatforms();
    } finally {
      setIsRemovingDuplicates(false);
    }
  };

  return (
    <section className={styles.page} data-testid="inbox-page">
      <header className={styles.hero}>
        <h1>Library</h1>
        <p className={styles.subtitle}>Everything you&apos;ve saved</p>
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
        <button
          type="button"
          className={styles.removeDuplicatesBtn}
          onClick={() => void handleRemoveDuplicates()}
          disabled={isRemovingDuplicates}
        >
          {isRemovingDuplicates ? 'Removing…' : 'Remove duplicates'}
        </button>
      </div>

      {contentStore.isLoading ? <p className={styles.message}>Refreshing queue…</p> : null}

      <ContentTable
        items={contentStore.items}
        onOpen={setSelectedContentId}
        onDelete={handleDelete}
        onSwipe={async (action) => handleKeep(action.content_id)}
        canSwipe={(item) => item.status !== 'archived'}
        sort={contentStore.sort}
        onSortChange={handleSortChange}
        keepActionLabel="Keep"
        keepActionTone="signal"
        keepActionIcon="archive"
        emptyMessage="Nothing saved yet. Use the extension to save articles, videos, and links."
      />

      <ContentDrawer
        contentId={selectedContentId}
        onClose={() => setSelectedContentId(null)}
      />
    </section>
  );
}
