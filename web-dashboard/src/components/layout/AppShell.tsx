import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import NavRail from './NavRail';
import TopBar from './TopBar';
import OnboardingModal, { hasSeenOnboarding } from '../ui/OnboardingModal';
import styles from './AppShell.module.css';

export default function AppShell() {
  const [showOnboarding, setShowOnboarding] = useState(!hasSeenOnboarding());

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
      {showOnboarding && (
        <OnboardingModal onClose={() => setShowOnboarding(false)} />
      )}
    </div>
  );
}
