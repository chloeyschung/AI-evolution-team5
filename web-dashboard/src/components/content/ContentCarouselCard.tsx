import { useState } from 'react';
import type { Content } from '../../types';
import { LogoShort } from '../Logo';
import styles from './ContentCarouselCard.module.css';

interface Props {
  content: Content;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 365) return `${Math.floor(days / 365)}년 전`;
  if (days > 30) return `${Math.floor(days / 30)}달 전`;
  if (days > 0) return `${days}일 전`;
  if (hours > 0) return `${hours}시간 전`;
  if (minutes > 0) return `${minutes}분 전`;
  return '방금 전';
}

function normalizeDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

export default function ContentCarouselCard({ content }: Props) {
  const [thumbError, setThumbError] = useState(false);

  const openSource = () => {
    window.open(content.url, '_blank', 'noopener,noreferrer');
  };

  const domain = normalizeDomain(content.url);
  const ago = timeAgo(content.created_at);

  return (
    <article
      className={styles.card}
      onClick={openSource}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') openSource();
      }}
      aria-label={content.title || domain}
      data-testid={`carousel-card-${content.id}`}
    >
      <div className={styles.thumb}>
        {content.thumbnail_url && !thumbError ? (
          <img
            src={content.thumbnail_url}
            alt=""
            className={styles.thumbImg}
            loading="lazy"
            onError={() => setThumbError(true)}
          />
        ) : (
          <div className={styles.thumbPlaceholder}>
            <div className={styles.thumbLogoWrap}>
              <LogoShort className={styles.thumbLogo} />
            </div>
          </div>
        )}
      </div>
      <div className={styles.body}>
        <h3 className={styles.title}>{content.title || content.url}</h3>
        <p className={styles.meta}>
          {domain} · {ago}
        </p>
      </div>
    </article>
  );
}
