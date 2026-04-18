import { NavLink } from 'react-router-dom';
import styles from './NavRail.module.css';

const navItems = [
  { label: 'Dashboard', to: '/dashboard', short: 'DS' },
  { label: 'Inbox', to: '/inbox', short: 'IB' },
  { label: 'Archive', to: '/archive', short: 'AR' },
  { label: 'Analytics', to: '/analytics', short: 'AN' },
  { label: 'Settings', to: '/settings', short: 'ST' },
];

export default function NavRail() {
  return (
    <aside className={styles.rail} data-testid="nav-rail">
      <div className={styles.brand}>
        <span className={styles.logo} aria-hidden="true">B</span>
        <div className={styles.brandText}>
          <strong>Briefly</strong>
          <span>Consume, don&apos;t hoard</span>
        </div>
      </div>

      <nav className={styles.nav} aria-label="Primary">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
            <span className={styles.short} aria-hidden="true">{item.short}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
