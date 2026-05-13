import { useState } from 'react';
import styles from './OnboardingModal.module.css';

const STORAGE_KEY = 'briefly_onboarding_seen';

const steps = [
  {
    image: '/assets/guide/06-dashboard.png',
    title: 'Dashboard',
    description: 'Quickly browse and triage your unread content in card form.',
    points: [
      'Keep — sends the card to Archive for later reference.',
      'Discard — moves the card to Trash (recoverable for 30 days).',
      'LLM bullet summary is shown on each card when available.',
      'Copy link copies the original URL to your clipboard.',
    ],
  },
  {
    image: '/assets/guide/07-library.png',
    title: 'Library',
    description: 'View and manage all saved content in a sortable table. Both inbox and archived items appear here.',
    points: [
      'Filter by Source to narrow down by platform (e.g. GitHub, YouTube).',
      'Click a title to open the detail drawer on the right.',
      'Remove duplicates cleans up entries with the same URL.',
      'Click column headers to sort by title, platform, status, or date.',
    ],
  },
  {
    image: '/assets/guide/08-content-detail-drawer.png',
    title: 'Content Detail',
    description: 'Click any title in Library or Archive to open the detail drawer — a quick preview before opening the full page.',
    points: [
      'Summary — LLM-generated bullet summary (if available).',
      'Metadata — status, content type, author, and created time.',
      'Open original content — opens the source URL in a new tab.',
    ],
  },
  {
    image: '/assets/guide/09-archive.png',
    title: 'Archive',
    description: 'All content you\'ve kept lands here. Review it, restore it to Library, or send it to Trash.',
    points: [
      'Restore icon — moves the item back to Library inbox.',
      'Trash icon — sends the archived item to Trash.',
      'Click a title to open the detail drawer.',
      'Same sort controls as Library.',
    ],
  },
  {
    image: '/assets/guide/10-trash.png',
    title: 'Trash',
    description: 'Deleted content is held here for 30 days. Restore anything before it\'s gone permanently.',
    points: [
      'Restore selected — returns checked items to Library inbox.',
      'Delete selected — permanently removes checked items.',
      'Use checkboxes to select individual items, or Select all.',
      'Permanent deletion cannot be undone — read the confirm dialog carefully.',
    ],
  },
  {
    image: '/assets/guide/11-analytics.png',
    title: 'Analytics',
    description: 'A snapshot of how much content you\'ve saved and processed.',
    points: [
      'Total cards — total content count in your Library.',
      'Kept / Cleared — how many you archived vs. discarded.',
      'Retention rate — percentage of processed items you chose to keep.',
      'Current streak — your consecutive processing streak.',
    ],
  },
  {
    image: '/assets/guide/12-settings.png',
    title: 'Settings',
    description: 'Customize how the dashboard looks and connects to the backend.',
    points: [
      'Theme — choose Light, Dark, or System.',
      'Default view — display Dashboard as Grid or List.',
      'Items per page — number of cards loaded at once.',
      'API base URL — the backend endpoint the dashboard calls.',
    ],
  },
];

export function hasSeenOnboarding() {
  return localStorage.getItem(STORAGE_KEY) === 'true';
}

export default function OnboardingModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0);
  const current = steps[step];
  const isLast = step === steps.length - 1;

  const handleClose = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    onClose();
  };

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Briefly onboarding">
      <div className={styles.modal}>
        <button className={styles.skipBtn} onClick={handleClose}>
          Skip
        </button>

        <div className={styles.imageWrap}>
          <img
            src={current.image}
            alt={current.title}
            className={styles.screenshot}
          />
        </div>

        <div className={styles.body}>
          <p className={styles.stepLabel}>{step + 1} / {steps.length}</p>
          <h2 className={styles.title}>{current.title}</h2>
          <p className={styles.description}>{current.description}</p>
          <ul className={styles.points}>
            {current.points.map((point, i) => (
              <li key={i} className={styles.point}>{point}</li>
            ))}
          </ul>
        </div>

        <div className={styles.footer}>
          <div className={styles.dots}>
            {steps.map((_, i) => (
              <button
                key={i}
                className={`${styles.dot} ${i === step ? styles.dotActive : ''}`}
                onClick={() => setStep(i)}
                aria-label={`Go to step ${i + 1}`}
              />
            ))}
          </div>

          <div className={styles.actions}>
            {step > 0 && (
              <button className={styles.backBtn} onClick={() => setStep(s => s - 1)}>
                Back
              </button>
            )}
            {isLast ? (
              <button className={styles.nextBtn} onClick={handleClose}>
                Get started
              </button>
            ) : (
              <button className={styles.nextBtn} onClick={() => setStep(s => s + 1)}>
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
