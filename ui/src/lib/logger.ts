/**
 * Client-side structured logging utility for Janus UI.
 *
 * Provides configurable logging levels, correlation ID tracking,
 * and optional remote log aggregation.
 */

import { applyPreReleaseHeader } from '@/lib/preRelease';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogContext {
  correlationId?: string;
  requestId?: string;
  component?: string;
  [key: string]: unknown;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context: LogContext;
  data?: Record<string, unknown>;
}

interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  remoteEndpoint?: string;
  bufferSize: number;
  flushIntervalMs: number;
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

// Default configuration
const defaultConfig: LoggerConfig = {
  enabled: true,
  level: (process.env.NEXT_PUBLIC_LOG_LEVEL as LogLevel) || 'info',
  remoteEndpoint: process.env.NEXT_PUBLIC_LOG_ENDPOINT,
  bufferSize: 50,
  flushIntervalMs: 5000,
};

class Logger {
  private config: LoggerConfig;
  private buffer: LogEntry[] = [];
  private context: LogContext = {};
  private flushTimer: ReturnType<typeof setInterval> | null = null;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
    this.startFlushTimer();
  }

  private startFlushTimer(): void {
    if (typeof window === 'undefined') return;
    if (this.flushTimer) clearInterval(this.flushTimer);
    if (this.config.remoteEndpoint) {
      this.flushTimer = setInterval(() => this.flush(), this.config.flushIntervalMs);
    }
  }

  private shouldLog(level: LogLevel): boolean {
    if (!this.config.enabled) return false;
    return LOG_LEVELS[level] >= LOG_LEVELS[this.config.level];
  }

  private formatMessage(level: LogLevel, message: string, data?: Record<string, unknown>): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      context: { ...this.context },
      data,
    };
  }

  private log(level: LogLevel, message: string, data?: Record<string, unknown>): void {
    if (!this.shouldLog(level)) return;

    const entry = this.formatMessage(level, message, data);

    // Console output based on level
    const consoleMethod = level === 'debug' ? 'log' : level;
    if (typeof console[consoleMethod] === 'function') {
      const contextStr = this.context.correlationId
        ? `[${this.context.correlationId}]`
        : '';
      const componentStr = this.context.component ? `[${this.context.component}]` : '';
      const prefix = [contextStr, componentStr].filter(Boolean).join(' ');

      if (data) {
        console[consoleMethod](`${prefix} ${message}`, data);
      } else {
        console[consoleMethod](`${prefix} ${message}`);
      }
    }

    // Buffer for remote sending
    if (this.config.remoteEndpoint) {
      this.buffer.push(entry);
      if (this.buffer.length >= this.config.bufferSize) {
        this.flush();
      }
    }
  }

  /**
   * Flush buffered logs to remote endpoint
   */
  async flush(): Promise<void> {
    if (!this.config.remoteEndpoint || this.buffer.length === 0) return;

    const entries = [...this.buffer];
    this.buffer = [];

    try {
      await fetch(this.config.remoteEndpoint, {
        method: 'POST',
        headers: applyPreReleaseHeader({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({ logs: entries }),
      });
    } catch (error) {
      // Re-add to buffer on failure, but cap to avoid memory issues
      this.buffer = [...entries.slice(-10), ...this.buffer].slice(0, this.config.bufferSize * 2);
      // Don't log the error to avoid infinite loop
      if (typeof console.error === 'function') {
        console.error('Failed to flush logs:', error);
      }
    }
  }

  /**
   * Set correlation ID for all subsequent logs
   */
  setCorrelationId(correlationId: string): void {
    this.context.correlationId = correlationId;
  }

  /**
   * Set request ID for all subsequent logs
   */
  setRequestId(requestId: string): void {
    this.context.requestId = requestId;
  }

  /**
   * Set component context for all subsequent logs
   */
  setComponent(component: string): void {
    this.context.component = component;
  }

  /**
   * Clear all context
   */
  clearContext(): void {
    this.context = {};
  }

  /**
   * Get a child logger with additional context
   */
  child(context: Partial<LogContext>): Logger {
    const child = new Logger({ ...this.config, remoteEndpoint: undefined }); // Child doesn't send remote
    child.context = { ...this.context, ...context };
    return child;
  }

  /**
   * Configure logger settings
   */
  configure(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
    this.startFlushTimer();
  }

  // Logging methods

  debug(message: string, data?: Record<string, unknown>): void {
    this.log('debug', message, data);
  }

  info(message: string, data?: Record<string, unknown>): void {
    this.log('info', message, data);
  }

  warn(message: string, data?: Record<string, unknown>): void {
    this.log('warn', message, data);
  }

  error(message: string, data?: Record<string, unknown>): void {
    this.log('error', message, data);
  }

  /**
   * Log an API request start
   */
  apiRequest(method: string, url: string, data?: Record<string, unknown>): void {
    this.debug(`API ${method} ${url}`, data);
  }

  /**
   * Log an API response
   */
  apiResponse(method: string, url: string, status: number, durationMs: number): void {
    const level: LogLevel = status >= 400 ? 'error' : status >= 300 ? 'warn' : 'debug';
    this.log(level, `API ${method} ${url} -> ${status}`, { status, durationMs });
  }

  /**
   * Log an SSE event
   */
  sseEvent(eventType: string, data?: Record<string, unknown>): void {
    this.debug(`SSE event: ${eventType}`, data);
  }

  /**
   * Log user interaction
   */
  userAction(action: string, data?: Record<string, unknown>): void {
    this.info(`User action: ${action}`, data);
  }

  /**
   * Log component lifecycle event
   */
  lifecycle(event: string, component: string, data?: Record<string, unknown>): void {
    this.debug(`${component} ${event}`, data);
  }

  /**
   * Log performance timing
   */
  timing(operation: string, durationMs: number, data?: Record<string, unknown>): void {
    this.info(`Timing: ${operation}`, { durationMs, ...data });
  }
}

// Singleton instance
const logger = new Logger();

// Export both the singleton and the class for testing/custom instances
export { Logger };
export default logger;
