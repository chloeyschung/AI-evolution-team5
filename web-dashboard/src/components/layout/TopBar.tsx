import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { useContentStore } from '../../stores/useContentStore';
import styles from './TopBar.module.css';

export default function TopBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.performLogout);
  const performSearch = useContentStore((state) => state.performSearch);

  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      void performSearch(query.trim());
    }, 300);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [query, performSearch]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className={styles.topBar} data-testid="top-bar">
      <label className={styles.searchLabel} htmlFor="global-search">Search</label>
      <input
        id="global-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search titles, authors, tags…"
        autoComplete="off"
        className={styles.searchInput}
      />
      <p className={styles.identity}>{user?.display_name || user?.email || 'Local session'}</p>
      <button className="btn" onClick={handleLogout}>Logout</button>
    </header>
  );
}
