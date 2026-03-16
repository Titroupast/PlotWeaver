import { ApiError } from "@/lib/api/shared";

export function mapApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.status === 422) {
      return `校验失败(422)：${error.message}`;
    }
    if (error.status === 409) {
      return `状态冲突(409)：${error.message}`;
    }
    return `${error.message}${error.traceId ? ` [trace_id=${error.traceId}]` : ""}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
