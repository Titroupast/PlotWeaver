const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";
const DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001";

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;
  traceId?: string | null;

  constructor(message: string, status: number, code?: string, details?: unknown, traceId?: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.traceId = traceId;
  }
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export function getTenantId(): string {
  return process.env.NEXT_PUBLIC_TENANT_ID ?? DEFAULT_TENANT_ID;
}

export async function parseJsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const rawText = await res.text();
    let payload: unknown = null;
    if (rawText) {
      try {
        payload = JSON.parse(rawText);
      } catch {
        throw new ApiError(`API ${res.status}: ${rawText}`, res.status);
      }
    }

    const objectPayload = payload as Record<string, unknown>;
    const message =
      typeof objectPayload?.message === "string"
        ? objectPayload.message
        : `API request failed with status ${res.status}`;
    const code = typeof objectPayload?.code === "string" ? objectPayload.code : undefined;
    const details = objectPayload?.details;
    const traceId = typeof objectPayload?.trace_id === "string" ? objectPayload.trace_id : null;
    throw new ApiError(message, res.status, code, details, traceId);
  }
  return (await res.json()) as T;
}
