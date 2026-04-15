import { useEffect } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentCard from '../components/content/ContentCard';
import styles from './Archive.module.css';

export default function Archive() {
  const contentStore = useContentStore();

  useEffect(() => {
    contentStore.updateFilters({ status: 'archived' });
    void contentStore.loadContent(1);
  }, []);

  const handleDelete = async (id: number) => {
    await contentStore.deleteItem(id);
  };

  return (
    <section className={styles.page} data-testid="archive-page">
      <header className={styles.hero}>
        <p className={styles.kicker}>Saved Wisdom</p>
        <h1>Your kept insights live here.</h1>
      </header>

      {contentStore.isLoading ? <p className={styles.message}>Loading your library…</p> : null}

      {!contentStore.items.length && !contentStore.isLoading ? (
        <p className={styles.message}>No kept cards yet. Hit Keep on any inbox card to build this library.</p>
      ) : null}

      <div className={styles.grid}>
        {contentStore.items.map((item) => (
          <ContentCard key={item.id} content={item} onDelete={handleDelete} />
        ))}
      </div>
    </section>
  );
}
