import { useEffect } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const contentStore = useContentStore();

  useEffect(() => {
    Promise.all([
      contentStore.loadContent(1),
      contentStore.loadPlatforms(),
    ]);
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

  return (
    <div className={styles.dashboard}>
      <div className={styles.pageHeader}>
        <h1>Dashboard</h1>
        <p>Your knowledge library at a glance</p>
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
          <p>No content found. Save something from the mobile app or browser extension!</p>
        </div>
      )}
    </div>
  );
}
