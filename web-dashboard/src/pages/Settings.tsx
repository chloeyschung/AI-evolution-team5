import { useEffect, useState } from 'react';
import type { AppSettings, ViewMode } from '../types';
import { DEFAULT_SETTINGS } from '../types';
import { resetApiClient } from '../api/client';
import styles from './Settings.module.css';

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings>({ ...DEFAULT_SETTINGS });
  const [savedSnapshot, setSavedSnapshot] = useState(() => JSON.stringify(DEFAULT_SETTINGS));
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const isDirty = JSON.stringify(settings) !== savedSnapshot;

  useEffect(() => {
    const saved = localStorage.getItem('briefly_settings');
    if (saved) {
      const parsed = { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
      setSettings(parsed);
      setSavedSnapshot(JSON.stringify(parsed));
    }
  }, []);

  useEffect(() => {
    if (!isDirty) {
      return undefined;
    }

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };

    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [isDirty]);

  const saveSettings = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    try {
      localStorage.setItem('briefly_settings', JSON.stringify(settings));
      document.documentElement.setAttribute('data-theme', settings.theme);
      resetApiClient();
      setSavedSnapshot(JSON.stringify(settings));
      setSaveMessage('Saved. Your workspace is updated.');
      setTimeout(() => setSaveMessage(null), 2500);
    } finally {
      setIsSaving(false);
    }
  };

  const viewModes: { value: ViewMode; label: string }[] = [
    { value: 'grid', label: 'Grid' },
    { value: 'list', label: 'List' },
  ];

  return (
    <section className={styles.page} data-testid="settings-page">
      <header className={styles.hero}>
        <p className={styles.kicker}>Control Room</p>
        <h1>Settings</h1>
      </header>

      {saveMessage ? <p className={styles.toast} role="status">{saveMessage}</p> : null}

      <div className={styles.sections}>
        {/* Appearance */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Appearance</h2>
          <div className={styles.card}>
            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>Theme</span>
                <span className={styles.settingDescription}>Light, dark, or follow system preference.</span>
              </div>
              <div className={styles.settingControl}>
                <select
                  id="theme"
                  value={settings.theme}
                  onChange={(e) => setSettings({ ...settings, theme: e.target.value as AppSettings['theme'] })}
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>Default view</span>
                <span className={styles.settingDescription}>How content is displayed on the Dashboard.</span>
              </div>
              <div className={styles.settingControl}>
                <select
                  id="default-view"
                  value={settings.defaultView}
                  onChange={(e) => setSettings({ ...settings, defaultView: e.target.value as ViewMode })}
                >
                  {viewModes.map((view) => (
                    <option key={view.value} value={view.value}>{view.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Feed */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Feed</h2>
          <div className={styles.card}>
            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>Items per page</span>
                <span className={styles.settingDescription}>How many articles load per request. Between 10 and 100.</span>
              </div>
              <div className={styles.settingControl}>
                <input
                  id="items-per-page"
                  type="number"
                  min={10}
                  max={100}
                  step={10}
                  value={settings.itemsPerPage}
                  onChange={(e) => setSettings({ ...settings, itemsPerPage: Number(e.target.value) })}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Developer */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Developer</h2>
          <div className={styles.card}>
            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>API base URL</span>
                <span className={styles.settingDescription}>
                  Override the backend endpoint. Leave blank to use the default (same origin or Vite proxy in dev).
                </span>
              </div>
              <div className={styles.settingControl}>
                <input
                  id="api-url"
                  type="url"
                  inputMode="url"
                  placeholder="http://localhost:8000"
                  value={settings.apiBaseUrl}
                  onChange={(e) => setSettings({ ...settings, apiBaseUrl: e.target.value.trim() })}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.saveBar}>
        <button onClick={saveSettings} disabled={isSaving || !isDirty}>
          {isSaving ? 'Saving…' : 'Save settings'}
        </button>
      </div>
    </section>
  );
}
