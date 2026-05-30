import { useEffect, useState } from 'react';
import { getStats, getUserStatistics, fetchSources, confirmSource, fetchNarrative, getCategoryStats } from '../api/endpoints';
import type { Stats, UserStatistics, SourceInsight, CategoryStats } from '../types';
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

  // Source Insights state
  const [sources, setSources] = useState<SourceInsight[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [narratives, setNarratives] = useState<Record<string, string>>({});
  const [narrativeLoading, setNarrativeLoading] = useState<Record<string, boolean>>({});
  const [addDomain, setAddDomain] = useState('');
  const [addingSource, setAddingSource] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [statsData, userStatsData, categoryData] = await Promise.all([
          getStats(),
          getUserStatistics(),
          getCategoryStats(),
        ]);
        setStats(statsData);
        setUserStats(userStatsData);
        setCategoryStats(categoryData);
      } catch (error) {
        console.error('Failed to load stats:', error);
      } finally {
        setIsLoading(false);
      }
    };
    void loadStats();
  }, []);

  useEffect(() => {
    const loadSources = async () => {
      setSourcesLoading(true);
      try {
        const data = await fetchSources();
        setSources(data);
      } catch (error) {
        console.error('Failed to load sources:', error);
      } finally {
        setSourcesLoading(false);
      }
    };
    void loadSources();
  }, []);

  const handleDetailClick = async (domain: string) => {
    if (expandedDomain === domain) {
      setExpandedDomain(null);
      return;
    }
    setExpandedDomain(domain);
    if (narratives[domain]) return;
    setNarrativeLoading((prev) => ({ ...prev, [domain]: true }));
    try {
      const result = await fetchNarrative(domain);
      setNarratives((prev) => ({ ...prev, [domain]: result.text }));
    } catch {
      setNarratives((prev) => ({ ...prev, [domain]: '' }));
    } finally {
      setNarrativeLoading((prev) => ({ ...prev, [domain]: false }));
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    const domain = addDomain.trim().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    if (!domain) return;
    setAddingSource(true);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const newSource = await confirmSource(domain, tz);
      setSources((prev) => {
        const exists = prev.find((s) => s.domain === newSource.domain);
        if (exists) return prev.map((s) => (s.domain === newSource.domain ? newSource : s));
        return [...prev, newSource];
      });
      setAddDomain('');
      setShowAddForm(false);
    } catch (error) {
      console.error('Failed to add source:', error);
    } finally {
      setAddingSource(false);
    }
  };

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

      {/* Source Insights */}
      <section data-testid="source-insights-section" style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>Trusted Sources</h2>
          <button
            type="button"
            data-testid="add-source-btn"
            onClick={() => setShowAddForm((v) => !v)}
            style={{ background: 'none', border: '1px solid currentColor', borderRadius: '4px', padding: '4px 10px', cursor: 'pointer' }}
          >
            +
          </button>
        </div>

        {showAddForm && (
          <form onSubmit={(e) => void handleAddSource(e)} style={{ display: 'flex', gap: '8px', marginBottom: '1rem' }}>
            <input
              type="text"
              value={addDomain}
              onChange={(e) => setAddDomain(e.target.value)}
              placeholder="e.g. theatlantic.com"
              style={{ flex: 1, padding: '6px 10px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
            <button type="submit" disabled={addingSource} style={{ padding: '6px 14px', borderRadius: '4px', cursor: 'pointer' }}>
              {addingSource ? 'Adding…' : 'Add'}
            </button>
          </form>
        )}

        {sourcesLoading ? (
          <p>Loading sources…</p>
        ) : sources.length === 0 ? (
          <p style={{ color: '#888' }}>
            No trusted sources yet. Keep articles from a domain and they&apos;ll appear here automatically.
          </p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {sources.map((source) => (
              <li
                key={source.domain}
                data-testid={`source-row-${source.domain}`}
                style={{
                  border: '1px solid #eee',
                  borderRadius: '8px',
                  padding: '12px',
                  marginBottom: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {/* Favicon — primary tap target opens site in default browser */}
                  <button
                    type="button"
                    data-testid={`favicon-btn-${source.domain}`}
                    aria-label={`Open ${source.domain}`}
                    onClick={() => window.open(`https://${source.domain}`, '_blank', 'noopener,noreferrer')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center', minWidth: '24px', minHeight: '24px' }}
                  >
                    <img
                      src={source.favicon_url ?? `https://${source.domain}/favicon.ico`}
                      alt={source.domain}
                      width={20}
                      height={20}
                      style={{ borderRadius: '2px' }}
                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                    />
                  </button>

                  <div style={{ flex: 1 }}>
                    <strong>{source.display_name ?? source.domain}</strong>
                    <span style={{ marginLeft: '8px', color: '#666', fontSize: '0.85em' }}>
                      {Math.round(source.keep_rate * 100)}% kept · {source.save_count} saves
                      {source.manually_added ? ' · added manually' : ''}
                    </span>
                  </div>

                  {/* Detail button — separate from favicon */}
                  <button
                    type="button"
                    onClick={() => void handleDetailClick(source.domain)}
                    style={{ padding: '4px 10px', borderRadius: '4px', border: '1px solid #ccc', cursor: 'pointer', background: 'none', fontSize: '0.85em' }}
                  >
                    {expandedDomain === source.domain ? 'Close' : 'Detail'}
                  </button>
                </div>

                {expandedDomain === source.domain && (
                  <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #eee' }}>
                    {narrativeLoading[source.domain] ? (
                      <p style={{ color: '#888' }}>Generating insight…</p>
                    ) : narratives[source.domain] ? (
                      <p style={{ lineHeight: '1.6', margin: 0 }}>{narratives[source.domain]}</p>
                    ) : (
                      <p style={{ color: '#888', margin: 0 }}>No narrative available yet.</p>
                    )}
                    {source.most_recent_title && (
                      <p style={{ color: '#888', fontSize: '0.85em', marginTop: '6px' }}>
                        Most recent: {source.most_recent_title}
                      </p>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
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
