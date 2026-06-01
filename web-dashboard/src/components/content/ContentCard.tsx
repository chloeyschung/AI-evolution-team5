import { useEffect, useRef, useState } from 'react';
import { Content, SwipeAction } from '../../types';
import { LogoShort } from '../Logo';
import PlatformIcon from '../ui/PlatformIcon';
import styles from './ContentCard.module.css';

interface ContentCardProps {
  content: Content;
  onDelete: (id: number) => void;
  onSwipe?: (action: SwipeAction) => void;
}

export default function ContentCard({ content, onDelete, onSwipe }: ContentCardProps) {
  const [copyFeedback, setCopyFeedback] = useState('');
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [thumbError, setThumbError] = useState(false);
  const copyFeedbackTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (copyFeedbackTimerRef.current !== null) {
        window.clearTimeout(copyFeedbackTimerRef.current);
      }
    };
  }, []);

  const createdAt = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(new Date(content.created_at));

  const handleDelete = () => {
    onDelete(content.id);
  };
  const openSource = () => {
    window.open(content.url, '_blank', 'noopener,noreferrer');
  };

  const copySource = async () => {
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable');
      }
      await navigator.clipboard.writeText(content.url);
      setCopyFeedback('Link copied!');
    } catch {
      setCopyFeedback('Copy failed');
    } finally {
      if (copyFeedbackTimerRef.current !== null) {
        window.clearTimeout(copyFeedbackTimerRef.current);
      }
      copyFeedbackTimerRef.current = window.setTimeout(() => {
        setCopyFeedback('');
      }, 1800);
    }
  };

  const rawSummary =
    content.summary || 'No summary yet. Open it once and Briefly will produce your bite-sized takeaway.';
  const hasBulletSummary =
    rawSummary.includes('\n') || rawSummary.trim().startsWith('•') || rawSummary.includes('\n•');

  const allBullets = rawSummary
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[•*-]\s*/, ''));

  const fullText = hasBulletSummary ? allBullets.join(' ') : rawSummary;
  const needsExpansion = fullText.length > 150;

  // 접힌 상태: 누적 150자 이내 bullet만 표시
  const collapsedBullets = (() => {
    let acc = 0;
    const result: string[] = [];
    for (const b of allBullets) {
      // 첫 번째 bullet은 150자를 초과해도 반드시 포함 — 아무것도 표시 안 되는 빈 카드 방지
      if (acc + b.length > 150 && result.length > 0) break;
      result.push(b);
      acc += b.length;
    }
    return result;
  })();

  const visibleBullets = summaryExpanded ? allBullets : collapsedBullets;
  const summaryText = hasBulletSummary
    ? rawSummary
    : summaryExpanded || rawSummary.length <= 150
      ? rawSummary
      : rawSummary.slice(0, 150) + '...';

  return (
    <article className={styles.card} data-testid={`content-card-${content.id}`}>
      <div className={styles.metaRow}>
        {content.auto_tag_category ? (
          <span className={styles.categoryBadge}>{content.auto_tag_category}</span>
        ) : null}
        <button type="button" className={styles.platformPill} onClick={openSource} aria-label="Open source">
          <PlatformIcon platform={content.platform} url={content.url} size={13} />
          <span className={styles.platformName}>{content.platform}</span>
        </button>
      </div>

      <div className={styles.body}>
        {content.thumbnail_url && !thumbError ? (
          <button type="button" className={styles.thumbButton} onClick={openSource} aria-label="Open source">
            <img
              src={content.thumbnail_url}
              alt=""
              className={styles.thumb}
              loading="lazy"
              onError={() => setThumbError(true)}
            />
          </button>
        ) : (
          <div className={styles.thumbPlaceholder} aria-hidden="true">
            <div className={styles.thumbLogoWrap}>
              <LogoShort className={styles.thumbLogo} />
            </div>
          </div>
        )}
        <h3 className={styles.title}>{content.title || content.url}</h3>
        {content.author ? <p className={styles.author}>by {content.author}</p> : null}
        {hasBulletSummary ? (
          <ul className={styles.summaryList}>
            {visibleBullets.map((line, index) => (
              <li key={`${content.id}-summary-${index}`} className={styles.summaryItem}>
                {line}
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.summary}>{summaryText}</p>
        )}
        {needsExpansion && (
          <button
            type="button"
            className={styles.expandBtn}
            onClick={() => setSummaryExpanded((v) => !v)}
          >
            {summaryExpanded ? '접기' : '더 보기'}
          </button>
        )}
      </div>

      {content.auto_tag_keywords_en?.length ? (
        <div className={styles.tagRow}>
          {content.auto_tag_keywords_en.slice(0, 8).map((kw) => (
            <span key={kw} className={styles.keyword}>{kw}</span>
          ))}
        </div>
      ) : null}

      <div className={styles.footerRow}>
        <span className={styles.date}>{createdAt}</span>
        <button
          type="button"
          className={`${styles.openLink} ${copyFeedback === 'Link copied!' ? styles.openLinkSuccess : ''}`}
          onClick={() => void copySource()}
          aria-live="polite"
          aria-atomic="true"
        >
          {copyFeedback || 'Copy link'}
        </button>
      </div>

      <div className={styles.actions}>
        {content.status === 'inbox' && onSwipe ? (
          <button
            onClick={() => onSwipe({ content_id: content.id, action: 'keep' })}
            className={`${styles.actionBtn} ${styles.keepBtn}`}
            aria-label="Keep — move to archive"
          >
            Keep
          </button>
        ) : null}
        <button
          onClick={handleDelete}
          className={`${styles.actionBtn} ${styles.deleteBtn}`}
          aria-label="Discard — move to trash"
        >
          Discard
        </button>
      </div>
    </article>
  );
}
