import { useEffect, useState, useCallback } from 'react';
import { getTrashContent, restoreContent, purgeContent } from '../api/endpoints';
import type { Content } from '../types';
import styles from './Trash.module.css';

export default function Trash() {
  const [items, setItems] = useState<Content[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const { items: trashItems } = await getTrashContent();
      setItems(trashItems);
      setSelectedIds(new Set());
    } catch {
      // ignore load errors and keep empty state
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const formatDate = (iso: string) =>
    new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).format(new Date(iso));

  const selectedCount = selectedIds.size;
  const allSelected = items.length > 0 && selectedCount === items.length;

  const toggleItem = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(items.map((item) => item.id)));
  };

  const handleRestore = async (id: number) => {
    try {
      await restoreContent(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch {
      alert('Could not restore item. The 30-day recovery window may have expired.');
    }
  };

  const handlePermanentDelete = async (id: number) => {
    if (!window.confirm('Permanently delete this item? This cannot be undone.')) return;
    try {
      await purgeContent(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch {
      alert('Failed to permanently delete item. Please try again.');
    }
  };

  const handleBulkRestore = async () => {
    if (selectedCount === 0) return;
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => restoreContent(id)));
      setItems((prev) => prev.filter((item) => !selectedIds.has(item.id)));
      setSelectedIds(new Set());
    } catch {
      alert('Failed to restore one or more items. Please try again.');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedCount === 0) return;
    if (!window.confirm(`Permanently delete ${selectedCount} selected item(s)? This cannot be undone.`)) return;
    try {
      await Promise.all(Array.from(selectedIds).map((id) => purgeContent(id)));
      setItems((prev) => prev.filter((item) => !selectedIds.has(item.id)));
      setSelectedIds(new Set());
    } catch {
      alert('Failed to delete one or more selected items. Please try again.');
    }
  };

  return (
    <section className={styles.page} data-testid="trash-page">
      <header className={styles.hero}>
        <div className={styles.heroText}>
          <h1>Trash</h1>
          <p className={styles.subtitle}>Items deleted in the last 30 days</p>
        </div>
      </header>

      {items.length > 0 ? (
        <div className={styles.toolbar}>
          <button className={styles.selectAllTextBtn} type="button" onClick={toggleAll}>
            {allSelected ? 'Unselect all' : 'Select all'}
          </button>
          <span className={styles.selectionCount}>{selectedCount} items selected</span>
          <div className={styles.bulkActions}>
            <button className={styles.bulkBtn} onClick={() => void handleBulkRestore()} disabled={selectedCount === 0}>
              Restore selected
            </button>
            <button className={styles.bulkDangerBtn} onClick={() => void handleBulkDelete()} disabled={selectedCount === 0}>
              Delete selected
            </button>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <p className={styles.message}>Loading trash…</p>
      ) : items.length === 0 ? (
        <p className={styles.message}>Trash is empty.</p>
      ) : (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.id} className={styles.row}>
              <label className={styles.checkboxWrap}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(item.id)}
                  onChange={() => toggleItem(item.id)}
                />
              </label>
              <div className={styles.rowInfo}>
                <span className={styles.rowTitle}>{item.title || item.url || 'Untitled'}</span>
                <span className={styles.rowMeta}>
                  {item.platform}{item.updated_at ? ` · Deleted ${formatDate(item.updated_at)}` : ''}
                </span>
              </div>
              <div className={styles.rowActions}>
                <button
                  className={styles.restoreBtn}
                  onClick={() => void handleRestore(item.id)}
                  aria-label="Restore item"
                  title="Restore"
                >
                  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                    <path d="M7 3a5 5 0 1 1-4.8 6.4.75.75 0 1 1 1.45-.38A3.5 3.5 0 1 0 7 4.5H4.8l1.7 1.7a.75.75 0 1 1-1.06 1.06L2.46 4.3a.75.75 0 0 1 0-1.06L5.44.26A.75.75 0 0 1 6.5 1.32L4.84 3H7Z" />
                  </svg>
                  <span className={styles.srOnly}>Restore</span>
                </button>
                <button
                  className={styles.clearBtn}
                  onClick={() => void handlePermanentDelete(item.id)}
                  aria-label="Permanently delete item"
                  title="Clear permanently"
                >
                  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                    <path d="M6 1.75A1.75 1.75 0 0 1 7.75 0h.5A1.75 1.75 0 0 1 10 1.75V2h3.25a.75.75 0 0 1 0 1.5h-.62l-.53 9.03A2 2 0 0 1 10.1 14.5H5.9a2 2 0 0 1-1.99-1.97L3.38 3.5h-.63a.75.75 0 1 1 0-1.5H6v-.25ZM7.5 2h1V1.75a.25.25 0 0 0-.25-.25h-.5a.25.25 0 0 0-.25.25V2Zm-2.62 1.5.53 9.03a.5.5 0 0 0 .49.47h4.2a.5.5 0 0 0 .5-.47l.52-9.03H4.88ZM6.75 5a.75.75 0 0 1 .75.75v4a.75.75 0 1 1-1.5 0v-4A.75.75 0 0 1 6.75 5Zm2.5 0a.75.75 0 0 1 .75.75v4a.75.75 0 1 1-1.5 0v-4A.75.75 0 0 1 9.25 5Z" />
                  </svg>
                  <span className={styles.srOnly}>Clear</span>
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
