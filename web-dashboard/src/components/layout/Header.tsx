import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { useContentStore } from '../../stores/useContentStore';
import styles from './Header.module.css';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: '📊' },
  { name: 'Inbox', path: '/inbox', icon: '📬' },
  { name: 'Archive', path: '/archive', icon: '📚' },
  { name: 'Analytics', path: '/analytics', icon: '📈' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
];

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const authStore = useAuthStore();
  const contentStore = useContentStore();

  const [searchQuery, setSearchQuery] = useState('');

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    await authStore.performLogout();
    navigate('/login');
  };

  // Debounced search
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleSearch = () => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      contentStore.performSearch(searchQuery);
    }, 300);
  };

  // Clean up debounce timer on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <div className={styles.logo} onClick={() => navigate('/dashboard')}>
          <span className={styles.logoIcon}>📚</span>
          <span className={styles.logoText}>Briefly</span>
        </div>

        <nav className={styles.nav}>
          {navItems.map((item) => (
            <a
              key={item.path}
              className={`${styles.navItem} ${isActive(item.path) ? styles.active : ''}`}
              href={item.path}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navText}>{item.name}</span>
            </a>
          ))}
        </nav>
      </div>

      <div className={styles.headerRight}>
        <div className={styles.searchBox}>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onInput={handleSearch}
            type="text"
            placeholder="Search..."
            className={styles.searchInput}
          />
        </div>

        <div className={styles.userMenu}>
          <span className={styles.userEmail}>{authStore.getUserEmail()}</span>
          <button onClick={handleLogout} className={styles.logoutBtn}>
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
