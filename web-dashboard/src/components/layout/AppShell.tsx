import { Outlet } from 'react-router-dom';
import NavRail from './NavRail';
import TopBar from './TopBar';
import styles from './AppShell.module.css';

export default function AppShell() {
  return (
    <div className={styles.shell}>
      <NavRail />
      <div className={styles.main}>
        <TopBar />
        <main id="main-content" className={styles.viewport}>
          <div className={styles.inner}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
