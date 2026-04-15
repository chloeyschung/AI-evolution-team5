import { useEffect, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import styles from './Inbox.module.css';

export default function Inbox() {
  const contentStore = useContentStore();
  const [selectedPlatform, setSelectedPlatform] = useState('');

  useEffect(() => {
    contentStore.updateFilters({ status: 'inbox' });
    contentStore.loadPlatforms();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await contentStore.deleteItem(id);
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const handleSwipe = async (action: { content_id: number; action: 'keep' | 'discard' }) => {
    try {
      await contentStore.performSwipe(action);
    } catch (error) {
      console.error('Swipe failed:', error);
    }
  };

  const handlePlatformChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const platform = e.target.value || undefined;
    setSelectedPlatform(e.target.value);
    contentStore.updateFilters({ platform });
  };

  return (
    <div className={styles.inbox}>
      <div className={styles.pageHeader}>
        <h1>Inbox</h1>
        <p>Content waiting to be processed</p>
      </div>

      <div className={styles.filters}>
        <label className={styles.filterLabel}>
          Platform:
          <select
            value={selectedPlatform}
            onChange={handlePlatformChange}
            className={styles.filterSelect}
          >
            <option value="">All Platforms</option>
            {contentStore.platforms.map((platform) => (
              <option key={platform.platform} value={platform.platform}>
                {platform.platform} ({platform.count})
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className={styles.contentGrid}>
        {contentStore.items.map((item) => (
          <ContentCard
            key={item.id}
            content={item}
            onDelete={handleDelete}
            onSwipe={handleSwipe}
          />
        ))}
      </div>

      {contentStore.isLoading && (
        <div className={styles.loading}>
          Loading...
        </div>
      )}

      {!contentStore.items.length && !contentStore.isLoading && (
        <div className={styles.empty}>
          <p>Your inbox is empty! 🎉</p>
        </div>
      )}
    </div>
  );
}
