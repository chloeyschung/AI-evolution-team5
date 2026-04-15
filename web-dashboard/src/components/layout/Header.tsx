import { useEffect, useRef, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { useContentStore } from '../../stores/useContentStore';
import styles from './Header.module.css';

const navItems = [
  { name: 'Now', path: '/dashboard' },
  { name: 'Inbox', path: '/inbox' },
  { name: 'Library', path: '/archive' },
  { name: 'Progress', path: '/analytics' },
  { name: 'Settings', path: '/settings' },
];

export default function Header() {
  const navigate = useNavigate();
  const authStore = useAuthStore();
  const contentStore = useContentStore();

  const [searchQuery, setSearchQuery] = useState('');
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleLogout = async () => {
    await authStore.performLogout();
    navigate('/login');
  };

  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      void contentStore.performSearch(searchQuery.trim());
    }, 220);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery]);

  return (
    <header className={styles.header}>
      <div className={styles.brandRow}>
        <button
          className={styles.brandButton}
          onClick={() => navigate('/dashboard')}
          aria-label="Go to dashboard"
        >
          <span className={styles.brandBadge} aria-hidden="true">B</span>
          <span className={styles.brandText}>Briefly</span>
          <span className={styles.brandTagline}>No Pain, Yes Gain</span>
        </button>

        <nav className={styles.nav} aria-label="Primary">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              {item.name}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className={styles.actionsRow}>
        <label className={styles.searchLabel} htmlFor="briefly-search">Search</label>
        <input
          id="briefly-search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          type="search"
          placeholder="Find by title or author…"
          className={styles.searchInput}
        />

        <span className={styles.userEmail}>{authStore.getUserEmail() || 'Local Session'}</span>
        <button onClick={handleLogout} className={styles.logoutBtn}>
          Logout
        </button>
      </div>
    </header>
  );
}
