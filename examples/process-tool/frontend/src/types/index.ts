/**
 * TypeScript types mirroring the Python ErrCode constants and Result class.
 */

/** Error codes matching Python ErrCode class. */
export const ErrCode = {
  OK: 0,
  UNKNOWN: 1,
  PARAM_INVALID: 2,
  NOT_IMPLEMENTED: 3,
  TIMEOUT: 4,
  INTERNAL_ERROR: 5,

  FILE_NOT_FOUND: 1001,
  FILE_READ_ERROR: 1002,
  FILE_WRITE_ERROR: 1003,
  FILE_FORMAT_INVALID: 1004,
  FILE_TOO_LARGE: 1005,
  PATH_NOT_ACCESSIBLE: 1006,

  PROCESS_START_FAILED: 2001,
  PROCESS_ALREADY_RUNNING: 2002,
  PROCESS_NOT_RUNNING: 2003,
  PROCESS_TIMEOUT: 2004,
  PROCESS_KILLED: 2005,

  API_CALL_FAILED: 3001,
  API_NOT_READY: 3002,
} as const;

/** Shape returned by Result.to_dict() in Python. */
export interface ApiResult<T = unknown> {
  code: number;
  msg: string;
  data: T;
}

/** Type guard: checks if an ApiResult is successful. */
export function isOk<T>(result: ApiResult<T>): result is ApiResult<T> & { code: 0 } {
  return result.code === ErrCode.OK;
}

/** Log entry forwarded from the Python backend. */
export interface LogEntry {
  id: number;
  level: string;
  message: string;
  timestamp?: string;
  class_name?: string;
}

/** Toast message options. */
export interface ToastOptions {
  id: number;
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;
}

/** Status badge state. */
export type StatusState = "idle" | "running" | "paused" | "error" | "done";

/** Process status data from get_status. */
export interface ProcessStatus {
  state: string;
  pid: number | null;
  timeout_remaining: number | null;
  output_count: number;
  elapsed: number | null;
}

/** Preset command definition. */
export interface PresetCommand {
  name: string;
  description: string;
  command: string;
  timeout: string;
}

/** System info data from get_system_info. */
export interface SystemInfo {
  system: string;
  release: string;
  version: string;
  machine: string;
  python_version: string;
  cpu_count: number | null;
  hostname: string;
  memory_total: number | null;
  memory_total_display?: string;
  memory_used?: number;
  memory_used_display?: string;
  memory_percent?: number;
  cpu_percent?: number | null;
}
