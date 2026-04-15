import { useEffect } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import styles from './Archive.module.css';

export default function Archive() {
  const contentStore = useContentStore();

  useEffect(() => {
    contentStore.updateFilters({ status: 'archived' });
    contentStore.loadContent(1);
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await contentStore.deleteItem(id);
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  return (
    <div className={styles.archive}>
      <div className={styles.pageHeader}>
        <h1>Archive</h1>
        <p>Your kept content library</p>
      </div>

      <div className={styles.contentGrid}>
        {contentStore.items.map((item) => (
          <ContentCard
            key={item.id}
            content={item}
            onDelete={handleDelete}
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
          <p>No archived content yet. Keep some items from your inbox!</p>
        </div>
      )}
    </div>
  );
}
