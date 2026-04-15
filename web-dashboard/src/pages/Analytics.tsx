import { useEffect, useState } from 'react';
import { getStats, getUserStatistics } from '../api/endpoints';
import type { Stats, UserStatistics } from '../types';
import styles from './Analytics.module.css';

export default function Analytics() {
  const [stats, setStats] = useState<Stats>({ pending: 0, kept: 0, discarded: 0 });
  const [userStats, setUserStats] = useState<UserStatistics>({
    total_swipes: 0,
    total_kept: 0,
    total_discarded: 0,
    retention_rate: 0,
    streak_days: 0,
    first_swipe_at: null,
    last_swipe_at: null,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [statsData, userStatsData] = await Promise.all([
          getStats(),
          getUserStatistics(),
        ]);
        setStats(statsData);
        setUserStats(userStatsData);
      } catch (error) {
        console.error('Failed to load stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadStats();
  }, []);

  const totalContent = () => stats.pending + stats.kept + stats.discarded;

  if (isLoading) {
    return (
      <div className={styles.analytics}>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  return (
    <div className={styles.analytics}>
      <div className={styles.pageHeader}>
        <h1>Analytics</h1>
        <p>Your reading insights and statistics</p>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{totalContent()}</div>
          <div className={styles.statLabel}>Total Content</div>
        </div>

        <div className={`${styles.statCard} ${styles.pending}`}>
          <div className={styles.statValue}>{stats.pending}</div>
          <div className={styles.statLabel}>In Inbox</div>
        </div>

        <div className={`${styles.statCard} ${styles.kept}`}>
          <div className={styles.statValue}>{stats.kept}</div>
          <div className={styles.statLabel}>Archived</div>
        </div>

        <div className={`${styles.statCard} ${styles.discarded}`}>
          <div className={styles.statValue}>{stats.discarded}</div>
          <div className={styles.statLabel}>Discarded</div>
        </div>
      </div>

      <div className={styles.detailedStats}>
        <h2>Detailed Statistics</h2>

        <div className={styles.statsRow}>
          <div className={styles.statItem}>
            <span className={styles.statItemLabel}>Total Swipes</span>
            <span className={styles.statItemValue}>{userStats.total_swipes}</span>
          </div>

          <div className={styles.statItem}>
            <span className={styles.statItemLabel}>Retention Rate</span>
            <span className={styles.statItemValue}>
              {(userStats.retention_rate * 100).toFixed(1)}%
            </span>
          </div>

          <div className={styles.statItem}>
            <span className={styles.statItemLabel}>Current Streak</span>
            <span className={styles.statItemValue}>{userStats.streak_days} days</span>
          </div>
        </div>

        <div className={styles.statsRow}>
          <div className={styles.statItem}>
            <span className={styles.statItemLabel}>First Swipe</span>
            <span className={styles.statItemValue}>
              {userStats.first_swipe_at
                ? new Date(userStats.first_swipe_at).toLocaleDateString()
                : 'N/A'}
            </span>
          </div>

          <div className={styles.statItem}>
            <span className={styles.statItemLabel}>Last Swipe</span>
            <span className={styles.statItemValue}>
              {userStats.last_swipe_at
                ? new Date(userStats.last_swipe_at).toLocaleDateString()
                : 'N/A'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
