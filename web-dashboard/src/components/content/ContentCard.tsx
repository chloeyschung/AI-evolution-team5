import { Content, SwipeAction } from '../../types';
import styles from './ContentCard.module.css';

interface ContentCardProps {
  content: Content;
  onDelete: (id: number) => void;
  onSwipe?: (action: SwipeAction) => void;
}

export default function ContentCard({ content, onDelete, onSwipe }: ContentCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      youtube: '📺',
      linkedin: '💼',
      twitter: '🐦',
      x: '🐦',
      medium: '✍️',
      instagram: '📷',
      facebook: '👍',
      tiktok: '🎵',
      reddit: '👽',
      web: '🌐',
    };
    return icons[platform.toLowerCase()] || '📄';
  };

  const handleKeep = () => {
    if (onSwipe) {
      onSwipe({ content_id: content.id, action: 'keep' });
    }
  };

  const handleDiscard = () => {
    if (onSwipe) {
      onSwipe({ content_id: content.id, action: 'discard' });
    }
  };

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this item?')) {
      onDelete(content.id);
    }
  };

  return (
    <article className={styles.contentCard}>
      <div className={styles.cardHeader}>
        <div className={styles.platformInfo}>
          <span className={styles.platformIcon}>{getPlatformIcon(content.platform)}</span>
          <span className={styles.platformName}>{content.platform}</span>
        </div>
        <div className={styles.cardActions}>
          {content.status === 'inbox' && onSwipe && (
            <>
              <button
                onClick={handleKeep}
                className={styles.keepBtn}
                title="Keep"
              >
                ✓
              </button>
              <button
                onClick={handleDiscard}
                className={styles.discardBtn}
                title="Discard"
              >
                ✕
              </button>
            </>
          )}
          <button onClick={handleDelete} className={styles.deleteBtn} title="Delete">
            🗑
          </button>
        </div>
      </div>

      <div className={styles.cardContent}>
        <h3 className={styles.cardTitle}>
          {content.title || 'Untitled'}
        </h3>

        {content.author && (
          <p className={styles.cardAuthor}>
            by {content.author}
          </p>
        )}

        {content.summary && (
          <p className={styles.cardSummary}>
            {content.summary}
          </p>
        )}
      </div>

      <div className={styles.cardFooter}>
        <span className={styles.cardDate}>{formatDate(content.created_at)}</span>
        <span className={`${styles.cardStatus} ${styles[content.status]}`}>
          {content.status === 'inbox' ? 'Inbox' : 'Archived'}
        </span>
      </div>

      <a
        href={content.url}
        target="_blank"
        rel="noopener noreferrer"
        className={styles.cardLink}
      >
        Open original →
      </a>
    </article>
  );
}
