import { useEffect, useState } from 'react';
import { getContentDetail } from '../../api/endpoints';
import type { Content } from '../../types';
import SlideDrawer from '../ui/SlideDrawer';
import styles from './ContentDrawer.module.css';

interface ContentDrawerProps {
  contentId: number | null;
  onClose: () => void;
}

export default function ContentDrawer({ contentId, onClose }: ContentDrawerProps) {
  const [detail, setDetail] = useState<Content | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const isOpen = contentId !== null;

  useEffect(() => {
    if (contentId === null) {
      setDetail(null);
      return;
    }

    const run = async () => {
      setIsLoading(true);
      try {
        const response = await getContentDetail(contentId);
        setDetail(response);
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [contentId]);

  return (
    <SlideDrawer
      title={detail?.title || 'Content detail'}
      subtitle={detail?.platform || 'Context and metadata'}
      isOpen={isOpen}
      onClose={onClose}
    >
      {isLoading ? <p>Loading detail…</p> : null}
      {detail ? (
        <>
          {detail.thumbnail_url ? (
            <img
              src={detail.thumbnail_url}
              alt=""
              className={styles.hero}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
          ) : null}

          <section className={styles.section}>
            <h3>Summary</h3>
            <p>{detail.summary || 'No summary is available yet for this item.'}</p>
          </section>

          <section className={styles.section}>
            <h3>Metadata</h3>
            <dl className={styles.metaList}>
              <div><dt>Status</dt><dd>{detail.status}</dd></div>
              <div><dt>Type</dt><dd>{detail.content_type}</dd></div>
              <div><dt>Author</dt><dd>{detail.author || 'N/A'}</dd></div>
              <div><dt>Created</dt><dd>{new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(detail.created_at))}</dd></div>
            </dl>
          </section>

          <section className={styles.section}>
            <h3>Source</h3>
            <a href={detail.url} target="_blank" rel="noreferrer">Open original content</a>
          </section>
        </>
      ) : null}
    </SlideDrawer>
  );
}
