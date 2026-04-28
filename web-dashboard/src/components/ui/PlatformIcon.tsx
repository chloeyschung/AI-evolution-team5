import { useState } from 'react';
import styles from './PlatformIcon.module.css';

const PLATFORM_SVGS: Record<string, React.ReactNode> = {
  youtube: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1C24 15.9 24 12 24 12s0-3.9-.5-5.8zM9.7 15.5V8.5l6.3 3.5-6.3 3.5z"/>
    </svg>
  ),
  linkedin: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20.4 20.4h-3.6v-5.6c0-1.3 0-3-1.8-3s-2.1 1.4-2.1 2.9v5.7H9.3V9h3.5v1.6h.1c.5-.9 1.6-1.8 3.3-1.8 3.5 0 4.2 2.3 4.2 5.4v6.2zM5.3 7.4a2.1 2.1 0 1 1 0-4.2 2.1 2.1 0 0 1 0 4.2zM7.1 20.4H3.5V9h3.6v11.4zM22.2 0H1.8C.8 0 0 .8 0 1.7v20.6C0 23.2.8 24 1.8 24h20.4c1 0 1.8-.8 1.8-1.7V1.7C24 .8 23.2 0 22.2 0z"/>
    </svg>
  ),
  twitter: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18.2 2h3.4l-7.4 8.5L23 22h-6.8l-5.3-7-6.1 7H1.4l7.9-9L1 2h7l4.8 6.3L18.2 2zm-1.2 18h1.9L7.1 4H5.1L17 20z"/>
    </svg>
  ),
  x: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18.2 2h3.4l-7.4 8.5L23 22h-6.8l-5.3-7-6.1 7H1.4l7.9-9L1 2h7l4.8 6.3L18.2 2zm-1.2 18h1.9L7.1 4H5.1L17 20z"/>
    </svg>
  ),
  reddit: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.8 7.4a1.3 1.3 0 1 1 0 2.6 1.3 1.3 0 0 1 0-2.6zm-5.8 1c3 0 5.5 1.9 5.5 4.3 0 .2 0 .4-.1.6.6.3 1 .9 1 1.5 0 1-.8 1.8-1.8 1.8-.4 0-.8-.1-1.1-.4a6.8 6.8 0 0 1-3.5.9 6.8 6.8 0 0 1-3.5-.9c-.3.3-.7.4-1.1.4-1 0-1.8-.8-1.8-1.8 0-.6.4-1.2 1-1.5 0-.2-.1-.4-.1-.6 0-2.4 2.5-4.3 5.5-4.3zM9 14a1 1 0 1 0 2 0 1 1 0 0 0-2 0zm4 0a1 1 0 1 0 2 0 1 1 0 0 0-2 0zm-4 2.5c.7.7 1.8 1 3 1s2.3-.3 3-1a.4.4 0 0 0-.6-.6c-.5.5-1.4.8-2.4.8s-1.9-.3-2.4-.8a.4.4 0 0 0-.6.6z"/>
    </svg>
  ),
  instagram: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2.2c3.2 0 3.6 0 4.9.1 3.3.1 4.8 1.7 4.9 4.9.1 1.3.1 1.6.1 4.8 0 3.2 0 3.6-.1 4.8-.1 3.2-1.7 4.8-4.9 4.9-1.3.1-1.6.1-4.9.1-3.2 0-3.6 0-4.8-.1-3.3-.1-4.8-1.7-4.9-4.9C2.2 15.6 2.2 15.2 2.2 12c0-3.2 0-3.6.1-4.8C2.4 3.9 4 2.3 7.2 2.3c1.2-.1 1.6-.1 4.8-.1zm0-2.2C8.7 0 8.3 0 7.1.1 2.7.3.3 2.7.1 7.1 0 8.3 0 8.7 0 12c0 3.3 0 3.7.1 4.9.2 4.4 2.6 6.8 7 7C8.3 24 8.7 24 12 24c3.3 0 3.7 0 4.9-.1 4.4-.2 6.8-2.6 7-7 .1-1.2.1-1.6.1-4.9 0-3.3 0-3.7-.1-4.9-.2-4.4-2.6-6.8-7-7C15.7 0 15.3 0 12 0zm0 5.8a6.2 6.2 0 1 0 0 12.4A6.2 6.2 0 0 0 12 5.8zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.4-11.8a1.4 1.4 0 1 0 0 2.9 1.4 1.4 0 0 0 0-2.9z"/>
    </svg>
  ),
  medium: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M13.5 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0zM19.5 12c0 3-1.3 5.5-3 5.5S13.5 15 13.5 12s1.3-5.5 3-5.5 3 2.5 3 5.5zM24 12c0 2.7-.5 4.9-1 4.9s-1-2.2-1-4.9.5-4.9 1-4.9 1 2.2 1 4.9z"/>
    </svg>
  ),
};

interface PlatformIconProps {
  platform: string;
  url?: string;
  size?: number;
}

const PLATFORM_BRAND_COLORS: Record<string, string> = {
  youtube: '#ff0000',
  linkedin: '#0a66c2',
  twitter: '#1d9bf0',
  x: '#111111',
  reddit: '#ff4500',
  instagram: '#e1306c',
  medium: '#12100e',
};

export default function PlatformIcon({ platform, url, size = 22 }: PlatformIconProps) {
  const [faviconFailed, setFaviconFailed] = useState(false);
  const platformKey = platform.toLowerCase();
  const knownSvg = PLATFORM_SVGS[platformKey];
  const brandColor = PLATFORM_BRAND_COLORS[platformKey] || 'currentColor';

  if (knownSvg) {
    return (
      <span className={styles.iconWrap} style={{ width: size, height: size, color: brandColor }}>
        {knownSvg}
      </span>
    );
  }

  if (url && !faviconFailed) {
    let domain = '';
    try {
      domain = new URL(url).hostname;
    } catch {
      // fall through to initials
    }

    if (domain) {
      return (
        <img
          src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
          alt=""
          width={size}
          height={size}
          className={styles.faviconImg}
          onError={() => setFaviconFailed(true)}
        />
      );
    }
  }

  // Fallback: first letter of platform name
  return (
    <span className={styles.initial} style={{ width: size, height: size }} aria-hidden="true">
      {platform.charAt(0).toUpperCase()}
    </span>
  );
}
