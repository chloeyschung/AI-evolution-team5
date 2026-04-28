export type BackendErrorEnvelope = {
  error?: unknown;
  message?: unknown;
  code?: unknown;
  details?: unknown;
  detail?: unknown;
};

export type ParsedApiError = {
  message: string;
  code?: string;
};

function stringifyCode(value: unknown): string | undefined {
  if (typeof value === 'string' && value.trim()) return value;
  if (typeof value === 'number') return String(value);
  return undefined;
}

export function parseApiErrorEnvelope(payload: unknown, fallback: string): ParsedApiError {
  if (!payload || typeof payload !== 'object') {
    return { message: fallback };
  }

  const envelope = payload as BackendErrorEnvelope;
  const detail = envelope.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return {
      message: detail,
      code: stringifyCode(envelope.code ?? envelope.error),
    };
  }

  if (detail && typeof detail === 'object') {
    const detailObj = detail as BackendErrorEnvelope;
    const message = typeof detailObj.message === 'string'
      ? detailObj.message
      : typeof detailObj.error === 'string'
        ? detailObj.error
        : fallback;

    return {
      message,
      code: stringifyCode(detailObj.code ?? detailObj.error ?? envelope.code ?? envelope.error),
    };
  }

  return {
    message: typeof envelope.message === 'string'
      ? envelope.message
      : typeof envelope.error === 'string'
        ? envelope.error
        : fallback,
    code: stringifyCode(envelope.code ?? envelope.error),
  };
}

export async function parseApiErrorResponse(response: Response, fallback: string): Promise<ParsedApiError> {
  const payload = await response.json().catch(() => undefined);
  return parseApiErrorEnvelope(payload, fallback);
}
