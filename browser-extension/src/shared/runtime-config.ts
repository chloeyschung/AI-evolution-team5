type RuntimeConfig = {
  GOOGLE_CLIENT_ID: string;
  API_BASE_URL: string;
  SHOW_API_URL_SETTING: boolean;
};

declare const __BRIEFLY_CONFIG: RuntimeConfig;

function normalizeBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

export function getRuntimeConfig(): RuntimeConfig {
  return __BRIEFLY_CONFIG;
}

export function resolveApiBaseUrl(configuredUrl: string): string {
  const configured = normalizeBaseUrl(configuredUrl);
  if (configured) return configured;

  const fromBuild = normalizeBaseUrl(getRuntimeConfig().API_BASE_URL || '');
  if (fromBuild) return fromBuild;

  throw new Error(
    'API base URL is not configured. Set VITE_API_BASE_URL at build time or enable the API URL setting.'
  );
}
