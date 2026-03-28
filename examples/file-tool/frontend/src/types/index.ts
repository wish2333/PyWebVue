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

/** Progress update payload. */
export interface ProgressPayload {
  current: number;
  total: number;
  label?: string;
}

/** Toast message options. */
export interface ToastOptions {
  id: number;
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;
}

/** File metadata returned by get_file_info. */
export interface FileInfo {
  path: string;
  name: string;
  extension: string;
  size_bytes: number;
  size_display: string;
  modified: string;
  is_binary: boolean;
}
