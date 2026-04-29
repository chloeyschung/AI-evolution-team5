import styles from './MetricCard.module.css';

interface MetricCardProps {
  label: string;
  value: string | number;
  hint?: string;
  tone?: 'default' | 'info' | 'success' | 'warning';
}

export default function MetricCard({ label, value, hint, tone = 'default' }: MetricCardProps) {
  return (
    <article className={`${styles.card} ${styles[tone]}`} data-testid="metric-card">
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
      {hint ? <p className={styles.hint}>{hint}</p> : null}
    </article>
  );
}
