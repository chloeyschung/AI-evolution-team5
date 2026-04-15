import { useEffect, useState } from 'react';
import type { AppSettings, ViewMode } from '../types';
import { DEFAULT_SETTINGS } from '../types';
import styles from './Settings.module.css';

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings>({ ...DEFAULT_SETTINGS });
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    // Load settings from localStorage
    const saved = localStorage.getItem('briefly_settings');
    if (saved) {
      setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(saved) });
    }
  }, []);

  const saveSettings = async () => {
    setIsSaving(true);
    setSaveMessage(null);

    try {
      localStorage.setItem('briefly_settings', JSON.stringify(settings));
      setSaveMessage('Settings saved successfully!');

      // Apply theme
      applyTheme(settings.theme);

      setTimeout(() => {
        setSaveMessage(null);
      }, 3000);
    } catch (error) {
      setSaveMessage('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const applyTheme = (theme: string) => {
    document.documentElement.setAttribute('data-theme', theme);
  };

  const viewModes: { value: ViewMode; label: string }[] = [
    { value: 'grid', label: 'Grid View' },
    { value: 'list', label: 'List View' },
  ];

  const themes: { value: string; label: string }[] = [
    { value: 'light', label: 'Light' },
    { value: 'dark', label: 'Dark' },
    { value: 'system', label: 'System' },
  ];

  return (
    <div className={styles.settings}>
      <div className={styles.pageHeader}>
        <h1>Settings</h1>
        <p>Customize your Briefly experience</p>
      </div>

      {saveMessage && (
        <div className={`${styles.message} ${styles.success}`}>
          {saveMessage}
        </div>
      )}

      <div className={styles.settingsCard}>
        <h2>Appearance</h2>

        <div className={styles.settingGroup}>
          <label className={styles.settingLabel}>Theme</label>
          <div className={styles.settingOptions}>
            {themes.map((theme) => (
              <button
                key={theme.value}
                className={`${styles.optionBtn} ${settings.theme === theme.value ? styles.active : ''}`}
                onClick={() => setSettings({ ...settings, theme: theme.value as any })}
              >
                {theme.label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.settingGroup}>
          <label className={styles.settingLabel}>Default View</label>
          <div className={styles.settingOptions}>
            {viewModes.map((view) => (
              <button
                key={view.value}
                className={`${styles.optionBtn} ${settings.defaultView === view.value ? styles.active : ''}`}
                onClick={() => setSettings({ ...settings, defaultView: view.value })}
              >
                {view.label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.settingGroup}>
          <label className={styles.settingLabel}>Items Per Page</label>
          <input
            type="number"
            min={10}
            max={100}
            step={10}
            value={settings.itemsPerPage}
            onChange={(e) =>
              setSettings({ ...settings, itemsPerPage: Number(e.target.value) })
            }
            className={styles.numberInput}
          />
        </div>
      </div>

      <div className={styles.settingsCard}>
        <h2>API Configuration</h2>

        <div className={styles.settingGroup}>
          <label className={styles.settingLabel} htmlFor="api-url">
            API Base URL
          </label>
          <input
            id="api-url"
            type="text"
            placeholder="http://localhost:8000"
            value={settings.apiBaseUrl}
            onChange={(e) =>
              setSettings({ ...settings, apiBaseUrl: e.target.value })
            }
            className={styles.textInput}
          />
          <p className={styles.settingHelp}>
            The URL of your Briefly backend API server.
          </p>
        </div>
      </div>

      <div className={styles.settingsActions}>
        <button onClick={saveSettings} disabled={isSaving} className={styles.saveBtn}>
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
