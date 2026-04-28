import { NavLink } from 'react-router-dom';
import styles from './NavRail.module.css';

function IconDashboard() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" />
      <rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" />
      <rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" />
      <rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" />
    </svg>
  );
}

function IconInbox() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M1.5 9.5h3l1.5 2h4l1.5-2h3" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function IconArchive() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="13" height="3" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <path d="M2.5 4.5v8a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-8" stroke="currentColor" strokeWidth="1.4" />
      <path d="M6 8h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M2.5 4.5h11M6.5 4.5V3h3v1.5M6 4.5v7.5M10 4.5v7.5M3.5 4.5l.75 8.25A1 1 0 0 0 5.24 14h5.52a1 1 0 0 0 .99-.75L12.5 4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconAnalytics() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.5" y="8" width="3" height="6" rx="0.75" fill="currentColor" />
      <rect x="6.5" y="5" width="3" height="9" rx="0.75" fill="currentColor" />
      <rect x="11.5" y="2" width="3" height="12" rx="0.75" fill="currentColor" />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="2.25" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M8 1.5v1.25M8 13.25V14.5M14.5 8h-1.25M2.75 8H1.5M12.36 3.64l-.88.88M4.52 11.48l-.88.88M12.36 12.36l-.88-.88M4.52 4.52l-.88-.88"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: <IconDashboard /> },
  { label: 'Library',   to: '/inbox',     icon: <IconInbox />     },
  { label: 'Archive',   to: '/archive',   icon: <IconArchive />   },
  { label: 'Trash',     to: '/trash',     icon: <IconTrash />     },
  { label: 'Analytics', to: '/analytics', icon: <IconAnalytics /> },
  { label: 'Settings',  to: '/settings',  icon: <IconSettings />  },
];

export default function NavRail() {
  return (
    <aside className={styles.rail} data-testid="nav-rail">
      <div className={styles.brand}>
        <svg className={styles.logo} viewBox="0 0 32 32" aria-hidden="true">
          <rect x="1" y="1" width="30" height="30" rx="9" fill="var(--color-signal)" />
          <path d="M9 10.5 C 9 9.67 9.67 9 10.5 9 H 17.2 C 20.4 9 22.6 10.8 22.6 13.6 C 22.6 15.2 21.7 16.4 20.4 17 C 22.1 17.6 23.2 19 23.2 20.9 C 23.2 23.9 20.8 26 17.2 26 H 10.5 C 9.67 26 9 25.33 9 24.5 Z M 13 12.5 V 16 H 16.5 C 17.8 16 18.6 15.3 18.6 14.25 C 18.6 13.2 17.8 12.5 16.5 12.5 Z M 13 19 V 22.5 H 17 C 18.4 22.5 19.2 21.75 19.2 20.75 C 19.2 19.75 18.4 19 17 19 Z" fill="var(--color-signal-on)" />
        </svg>
        <div className={styles.brandText}>
          <strong>Briefly</strong>
          <span>Consume, don&apos;t hoard</span>
        </div>
      </div>

      <nav className={styles.nav} aria-label="Primary">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
            <span className={styles.iconWrap} aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
