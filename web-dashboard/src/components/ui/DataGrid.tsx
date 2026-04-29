import type { ReactNode } from 'react';
import styles from './DataGrid.module.css';

export interface DataGridColumn<T> {
  key: string;
  header: ReactNode;
  width?: string;
  align?: 'left' | 'center' | 'right';
  ariaSort?: 'ascending' | 'descending' | 'none';
  render: (item: T) => ReactNode;
}

interface DataGridProps<T> {
  columns: DataGridColumn<T>[];
  rows: T[];
  rowKey: (item: T) => string | number;
  emptyMessage: string;
}

export default function DataGrid<T>({ columns, rows, rowKey, emptyMessage }: DataGridProps<T>) {
  if (!rows.length) {
    return <div className={styles.empty}>{emptyMessage}</div>;
  }

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                style={{ width: column.width, textAlign: column.align || 'left' }}
                scope="col"
                aria-sort={column.ariaSort}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={`${rowKey(row)}-${column.key}`} style={{ textAlign: column.align || 'left' }}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
