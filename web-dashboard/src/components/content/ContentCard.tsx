import { Content, SwipeAction } from '../../types';
import styles from './ContentCard.module.css';

interface ContentCardProps {
  content: Content;
  onDelete: (id: number) => void;
  onSwipe?: (action: SwipeAction) => void;
}

const PLATFORM_ICONS: Record<string, string> = {
  youtube: 'Play',
  linkedin: 'In',
  twitter: 'X',
  x: 'X',
  medium: 'M',
  instagram: 'IG',
  facebook: 'F',
  tiktok: 'TT',
  reddit: 'R',
  web: 'Web',
};

export default function ContentCard({ content, onDelete, onSwipe }: ContentCardProps) {
  const createdAt = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(new Date(content.created_at));

  const platformKey = content.platform.toLowerCase();

  const handleDelete = () => {
    if (window.confirm('Remove this item from Briefly?')) {
      onDelete(content.id);
    }
  };

  return (
    <article className={styles.card} data-testid={`content-card-${content.id}`}>
      <div className={styles.metaRow}>
        <div className={styles.platformPill}>
          <span className={styles.platformMark} aria-hidden="true">{PLATFORM_ICONS[platformKey] || 'Doc'}</span>
          <span className={styles.platformName}>{content.platform}</span>
        </div>
        <span className={`${styles.statusPill} ${content.status === 'inbox' ? styles.inbox : styles.archive}`}>
          {content.status === 'inbox' ? 'Ready to digest' : 'Captured'}
        </span>
      </div>

      <div className={styles.body}>
        {content.thumbnail_url ? (
          <img
            src={content.thumbnail_url}
            alt=""
            className={styles.thumb}
            loading="lazy"
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
          />
        ) : null}
        <h3 className={styles.title}>{content.title || content.url}</h3>
        {content.author ? <p className={styles.author}>by {content.author}</p> : null}
        <p className={styles.summary}>
          {content.summary || 'No summary yet. Open it once and Briefly will produce your bite-sized takeaway.'}
        </p>
      </div>

      <div className={styles.footerRow}>
        <span className={styles.date}>{createdAt}</span>
        <a href={content.url} target="_blank" rel="noopener noreferrer" className={styles.openLink}>
          Open source
        </a>
      </div>

      <div className={styles.actions}>
        {content.status === 'inbox' && onSwipe ? (
          <>
            <button
              onClick={() => onSwipe({ content_id: content.id, action: 'keep' })}
              className={`${styles.actionBtn} ${styles.keepBtn}`}
              aria-label="Keep this card"
            >
              Keep
            </button>
            <button
              onClick={() => onSwipe({ content_id: content.id, action: 'discard' })}
              className={`${styles.actionBtn} ${styles.discardBtn}`}
              aria-label="Discard this card"
            >
              Clear
            </button>
          </>
        ) : null}
        <button
          onClick={handleDelete}
          className={`${styles.actionBtn} ${styles.deleteBtn}`}
          aria-label="Delete this card"
        >
          Delete
        </button>
      </div>
    </article>
  );
}
