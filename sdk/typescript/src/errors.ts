/** Matches flopsindex.exceptions in Python. */

export interface FlopsErrorDetail {
  statusCode?: number;
  detail?: unknown;
}

export class FlopsError extends Error {
  readonly statusCode?: number;
  readonly detail?: unknown;

  constructor(message: string, opts: FlopsErrorDetail = {}) {
    super(message);
    this.name = "FlopsError";
    this.statusCode = opts.statusCode;
    this.detail = opts.detail;
    // Restore prototype chain for instanceof across transpilation targets.
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** 401 / 403 — endpoint requires an API key, or the key is invalid. */
export class FlopsAuthError extends FlopsError {
  constructor(message: string, opts: FlopsErrorDetail = {}) {
    super(message, opts);
    this.name = "FlopsAuthError";
  }
}

/** 404 — unknown index slug, or not on the requested public surface. */
export class FlopsNotFoundError extends FlopsError {
  constructor(message: string, opts: FlopsErrorDetail = {}) {
    super(message, opts);
    this.name = "FlopsNotFoundError";
  }
}

/** 429 — rate limited. `retryAfterSeconds` echoes the Retry-After header. */
export class FlopsRateLimitError extends FlopsError {
  readonly retryAfterSeconds: number;

  constructor(
    message: string,
    opts: FlopsErrorDetail & { retryAfterSeconds?: number } = {},
  ) {
    super(message, opts);
    this.name = "FlopsRateLimitError";
    this.retryAfterSeconds = opts.retryAfterSeconds ?? 60;
  }
}

/** 5xx — upstream server error. */
export class FlopsServerError extends FlopsError {
  constructor(message: string, opts: FlopsErrorDetail = {}) {
    super(message, opts);
    this.name = "FlopsServerError";
  }
}
