import type { PropsWithChildren } from 'react';
import styles from './SlideDrawer.module.css';

interface SlideDrawerProps {
  title: string;
  subtitle?: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function SlideDrawer({
  title,
  subtitle,
  isOpen,
  onClose,
  children,
}: PropsWithChildren<SlideDrawerProps>) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <aside className={styles.drawer} onClick={(event) => event.stopPropagation()} aria-label={title}>
        <header className={styles.head}>
          <div>
            <h2>{title}</h2>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          <button className="btn" onClick={onClose} aria-label="Close detail panel">Close</button>
        </header>
        <div className={styles.content}>{children}</div>
      </aside>
    </div>
  );
}
