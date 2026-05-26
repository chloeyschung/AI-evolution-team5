import { useEffect, useState } from 'react';
import { getStats, getUserStatistics, getCategoryStats } from '../api/endpoints';
import type { Stats, UserStatistics, CategoryStats } from '../types';
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
  const [categoryStats, setCategoryStats] = useState<CategoryStats>({ categories: [] });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [statsData, userStatsData] = await Promise.all([getStats(), getUserStatistics()]);
        setStats(statsData);
        setUserStats(userStatsData);
      } catch (error) {
        console.error('Failed to load stats:', error);
      } finally {
        setIsLoading(false);
      }

      try {
        const categoryData = await getCategoryStats();
        setCategoryStats(categoryData);
      } catch (error) {
        console.error('Failed to load category stats:', error);
      }
    };

    void loadStats();
  }, []);

  if (isLoading) {
    return <section className={styles.page}><p className={styles.message}>Loading your progress…</p></section>;
  }

  const total = stats.pending + stats.kept + stats.discarded;

  return (
    <section className={styles.page} data-testid="analytics-page">
      <header className={styles.hero}>
        <p className={styles.kicker}>Knowledge Gain</p>
        <h1>Measure learning momentum, not backlog.</h1>
      </header>

      <div className={styles.statGrid}>
        <article className={styles.statCard}><h2>{total}</h2><p>Total cards</p></article>
        <article className={styles.statCard}><h2>{stats.pending}</h2><p>To digest</p></article>
        <article className={styles.statCard}><h2>{stats.kept}</h2><p>Kept</p></article>
        <article className={styles.statCard}><h2>{stats.discarded}</h2><p>Cleared</p></article>
      </div>

      <section className={styles.detailCard}>
        <div><span>Total swipes</span><strong>{userStats.total_swipes}</strong></div>
        <div><span>Retention rate</span><strong>{(userStats.retention_rate * 100).toFixed(1)}%</strong></div>
        <div><span>Current streak</span><strong>{userStats.streak_days} days</strong></div>
      </section>

      {categoryStats.categories.length > 0 && (
        <section className={styles.categorySection}>
          <h2 className={styles.sectionTitle}>Kept by category</h2>
          <div className={styles.categoryList}>
            {categoryStats.categories.map(({ category, total: catTotal, kept }) => {
              const pct = catTotal > 0 ? Math.round((kept / catTotal) * 100) : 0;
              return (
                <div key={category} className={styles.categoryRow}>
                  <span className={styles.categoryName}>{category}</span>
                  <div className={styles.barTrack}>
                    <div className={styles.barFill} style={{ width: `${pct}%` }} />
                  </div>
                  <span className={styles.categoryMeta}>{kept}/{catTotal}</span>
                  <span className={styles.categoryPct}>{pct}%</span>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </section>
  );
}
