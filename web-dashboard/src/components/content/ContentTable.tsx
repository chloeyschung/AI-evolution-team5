import { useEffect, useRef } from 'react';
import DataGrid, { type DataGridColumn } from '../ui/DataGrid';
import type { Content, SwipeAction } from '../../types';
import styles from './ContentTable.module.css';

interface ContentTableProps {
  items: Content[];
  onOpen: (id: number) => void;
  onDelete: (id: number) => Promise<void>;
  onSwipe?: (action: SwipeAction) => Promise<void>;
  keepActionLabel?: string;
  keepActionTone?: 'neutral' | 'signal';
  keepActionIcon?: 'undo' | 'archive';
  canSwipe?: (item: Content) => boolean;
  emptyMessage: string;
}

function formatDate(iso: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(new Date(iso));
}

/** Collapse a multi-bullet AI summary into one inline string so table rows
 *  stay even-height. CSS line-clamps to 2 lines after this. */
function flattenSummary(raw?: string | null) {
  if (!raw) return 'No summary yet.';
  const parts = raw
    .split('\n')
    .map((line) => line.trim().replace(/^[•*\-–]\s*/, ''))
    .filter(Boolean);
  if (parts.length === 0) return raw;
  if (parts.length === 1) return parts[0];
  return parts.join(' · ');
}

export default function ContentTable({
  items,
  onOpen,
  onDelete,
  onSwipe,
  keepActionLabel = 'Keep',
  keepActionTone = 'signal',
  keepActionIcon = 'undo',
  canSwipe,
  emptyMessage,
}: ContentTableProps) {
  const tableHostRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const host = tableHostRef.current;
    if (!host) return;

    const rows = host.querySelectorAll('tbody tr');
    rows.forEach((row) => {
      row.setAttribute('data-testid', 'content-table-row');
      row.classList.add('content-table-row');
    });
  }, [items]);

  const columns: DataGridColumn<Content>[] = [
    {
      key: 'title',
      header: 'Title',
      width: '32%',
      render: (item) => (
        <button className={styles.titleButton} onClick={() => onOpen(item.id)}>
          <strong>{item.title || item.url || 'Untitled content'}</strong>
          {item.author ? <span>by {item.author}</span> : null}
        </button>
      ),
    },
    {
      key: 'platform',
      header: 'Platform',
      width: '14%',
      render: (item) => <span className={styles.platform}>{item.platform}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '12%',
      render: (item) => (
        <span className={`badge ${item.status === 'inbox' ? 'badge-inbox' : 'badge-archived'}`}>
          {item.status}
        </span>
      ),
    },
    {
      key: 'summary',
      header: 'Summary',
      width: '26%',
      render: (item) => <span className={styles.summary}>{flattenSummary(item.summary)}</span>,
    },
    {
      key: 'date',
      header: 'Created',
      width: '10%',
      render: (item) => <span className={styles.date}>{formatDate(item.created_at)}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '18%',
      render: (item) => {
        const swipeEnabled = onSwipe ? (canSwipe ? canSwipe(item) : true) : false;
        return (
        <div className={styles.actions}>
          {onSwipe ? (
            <button
              className={`${styles.iconAction} ${keepActionTone === 'signal' ? styles.iconActionKeep : ''}`}
              onClick={() => void onSwipe({ content_id: item.id, action: 'keep' })}
              aria-label={`${keepActionLabel} item`}
              title={keepActionLabel}
              disabled={!swipeEnabled}
            >
              {keepActionIcon === 'archive' ? (
                <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                  <rect x="1.5" y="1.5" width="13" height="3" rx="1" fill="none" stroke="currentColor" strokeWidth="1.4" />
                  <path d="M2.5 4.5v8a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-8" fill="none" stroke="currentColor" strokeWidth="1.4" />
                  <path d="M6 8h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                </svg>
              ) : (
                <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                  <path d="M7 3a5 5 0 1 1-4.8 6.4.75.75 0 1 1 1.45-.38A3.5 3.5 0 1 0 7 4.5H4.8l1.7 1.7a.75.75 0 1 1-1.06 1.06L2.46 4.3a.75.75 0 0 1 0-1.06L5.44.26A.75.75 0 0 1 6.5 1.32L4.84 3H7Z" />
                </svg>
              )}
            </button>
          ) : null}
          <button
            className={`${styles.iconAction} ${styles.iconActionDanger}`}
            onClick={() => void onDelete(item.id)}
            aria-label="Discard item"
            title="Discard"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
              <path d="M6 1.75A1.75 1.75 0 0 1 7.75 0h.5A1.75 1.75 0 0 1 10 1.75V2h3.25a.75.75 0 0 1 0 1.5h-.62l-.53 9.03A2 2 0 0 1 10.1 14.5H5.9a2 2 0 0 1-1.99-1.97L3.38 3.5h-.63a.75.75 0 1 1 0-1.5H6v-.25ZM7.5 2h1V1.75a.25.25 0 0 0-.25-.25h-.5a.25.25 0 0 0-.25.25V2Zm-2.62 1.5.53 9.03a.5.5 0 0 0 .49.47h4.2a.5.5 0 0 0 .5-.47l.52-9.03H4.88ZM6.75 5a.75.75 0 0 1 .75.75v4a.75.75 0 1 1-1.5 0v-4A.75.75 0 0 1 6.75 5Zm2.5 0a.75.75 0 0 1 .75.75v4a.75.75 0 1 1-1.5 0v-4A.75.75 0 0 1 9.25 5Z" />
            </svg>
          </button>
        </div>
      );
      },
    },
  ];

  return (
    <div ref={tableHostRef} className={styles.tableHost}>
      <DataGrid
        columns={columns}
        rows={items}
        rowKey={(item) => item.id}
        emptyMessage={emptyMessage}
      />
    </div>
  );
}
