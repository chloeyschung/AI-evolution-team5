import { useEffect, useState } from 'react';
import type { AppSettings, ViewMode } from '../types';
import { DEFAULT_SETTINGS } from '../types';
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
        <h1>Tune Briefly for your daily rhythm.</h1>
      </header>

      {saveMessage ? <p className={styles.toast} role="status">{saveMessage}</p> : null}

      <div className={styles.form}>
        <label htmlFor="theme">Theme</label>
        <select
          id="theme"
          value={settings.theme}
          onChange={(e) => setSettings({ ...settings, theme: e.target.value as AppSettings['theme'] })}
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="system">System</option>
        </select>

        <label htmlFor="default-view">Default view</label>
        <select
          id="default-view"
          value={settings.defaultView}
          onChange={(e) => setSettings({ ...settings, defaultView: e.target.value as ViewMode })}
        >
          {viewModes.map((view) => <option key={view.value} value={view.value}>{view.label}</option>)}
        </select>

        <label htmlFor="items-per-page">Items per page</label>
        <input
          id="items-per-page"
          type="number"
          min={10}
          max={100}
          step={10}
          value={settings.itemsPerPage}
          onChange={(e) => setSettings({ ...settings, itemsPerPage: Number(e.target.value) })}
        />

        <label htmlFor="api-url">API base URL</label>
        <input
          id="api-url"
          type="url"
          inputMode="url"
          value={settings.apiBaseUrl}
          onChange={(e) => setSettings({ ...settings, apiBaseUrl: e.target.value.trim() })}
        />

        <button onClick={saveSettings} disabled={isSaving || !isDirty}>
          {isSaving ? 'Saving…' : 'Save settings'}
        </button>
      </div>
    </section>
  );
}
