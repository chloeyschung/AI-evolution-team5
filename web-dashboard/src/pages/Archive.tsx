import { useEffect, useState } from 'react';
import { useContentStore } from '../stores/useContentStore';
import ContentDrawer from '../components/content/ContentDrawer';
import ContentTable from '../components/content/ContentTable';
import styles from './Archive.module.css';

export default function Archive() {
  const contentStore = useContentStore();
  const [selectedContentId, setSelectedContentId] = useState<number | null>(null);

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
        <h1>Archive</h1>
        <p className={styles.subtitle}>Completed and deferred items</p>
      </header>

      {contentStore.isLoading ? <p className={styles.message}>Loading your library…</p> : null}

      <ContentTable
        items={contentStore.items}
        onOpen={setSelectedContentId}
        onDelete={handleDelete}
        emptyMessage="No completed or deferred items in archive."
      />

      <ContentDrawer
        contentId={selectedContentId}
        onClose={() => setSelectedContentId(null)}
      />
    </section>
  );
}
