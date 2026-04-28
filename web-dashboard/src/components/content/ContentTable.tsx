import { useEffect, useRef } from 'react';
import DataGrid, { type DataGridColumn } from '../ui/DataGrid';
import type { Content, SwipeAction } from '../../types';
import styles from './ContentTable.module.css';

interface ContentTableProps {
  items: Content[];
  onOpen: (id: number) => void;
  onDelete: (id: number) => Promise<void>;
  onSwipe?: (action: SwipeAction) => Promise<void>;
  emptyMessage: string;
}

function formatDate(iso: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(new Date(iso));
}

export default function ContentTable({
  items,
  onOpen,
  onDelete,
  onSwipe,
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
          <span>{item.author || item.platform}</span>
        </button>
      ),
    },
    {
      key: 'platform',
      header: 'Platform',
      width: '14%',
      render: (item) => item.platform,
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
      render: (item) => <span className={styles.summary}>{item.summary || 'No summary yet.'}</span>,
    },
    {
      key: 'date',
      header: 'Created',
      width: '10%',
      render: (item) => formatDate(item.created_at),
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '18%',
      render: (item) => (
        <div className={styles.actions}>
          {item.status === 'inbox' && onSwipe ? (
            <>
              <button className="btn" onClick={() => void onSwipe({ content_id: item.id, action: 'keep' })}>Keep</button>
              <button className="btn" onClick={() => void onSwipe({ content_id: item.id, action: 'discard' })}>Discard</button>
            </>
          ) : null}
          <button className="btn btn-danger" onClick={() => void onDelete(item.id)}>Delete</button>
        </div>
      ),
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
