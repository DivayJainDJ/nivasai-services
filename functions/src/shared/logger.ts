/**
 * Structured Cloud Logging wrapper for NivasAI Services
 */

import { logger as cloudLogger } from 'firebase-functions/v1';

// ============================================================================
// Logger Configuration
// ============================================================================

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

export interface ILogEntry {
  readonly level: LogLevel;
  readonly message: string;
  readonly timestamp: Date;
  readonly service?: string;
  readonly function?: string;
  readonly requestId?: string;
  readonly userId?: string;
  readonly wardId?: string;
  readonly complaintId?: string;
  readonly duration?: number;
  readonly error?: {
    readonly message: string;
    readonly stack?: string;
    readonly code?: string;
  };
  readonly metadata?: Record<string, unknown>;
}

// ============================================================================
// Logger Class
// ============================================================================

export class Logger {
  private readonly serviceName: string;
  private readonly functionName: string;
  private readonly requestId: string;

  constructor(serviceName: string, functionName?: string) {
    this.serviceName = serviceName;
    this.functionName = functionName || '';
    this.requestId = this.generateRequestId();
  }

  // ============================================================================
  // Public API
  // ============================================================================

  debug(message: string, metadata?: Record<string, unknown>): void {
    this.log(LogLevel.DEBUG, message, metadata);
  }

  info(message: string, metadata?: Record<string, unknown>): void {
    this.log(LogLevel.INFO, message, metadata);
  }

  warn(message: string, metadata?: Record<string, unknown>): void {
    this.log(LogLevel.WARN, message, metadata);
  }

  error(message: string, error?: Error | Record<string, unknown>, metadata?: Record<string, unknown>): void {
    let errorData: Record<string, unknown> | undefined;

    if (error instanceof Error) {
      errorData = {
        message: error.message,
        stack: error.stack,
        name: error.name,
      };
    } else if (error) {
      errorData = error;
    }

    this.log(LogLevel.ERROR, message, { ...metadata, error: errorData });
  }

  // ============================================================================
  // Performance Logging
  // ============================================================================

  startTimer(operation: string): () => void {
    const startTime = Date.now();
    
    return () => {
      const duration = Date.now() - startTime;
      this.info(`Operation completed: ${operation}`, { duration, operation });
    };
  }

  logFunctionStart(params?: Record<string, unknown>): void {
    this.info(`Function started: ${this.functionName}`, {
      function: this.functionName,
      requestId: this.requestId,
      ...params,
    });
  }

  logFunctionEnd(params?: Record<string, unknown>): void {
    this.info(`Function completed: ${this.functionName}`, {
      function: this.functionName,
      requestId: this.requestId,
      ...params,
    });
  }

  logFunctionError(error: Error, params?: Record<string, unknown>): void {
    this.error(`Function failed: ${this.functionName}`, error, {
      function: this.functionName,
      requestId: this.requestId,
      ...params,
    });
  }

  // ============================================================================
  // Structured Logging Methods
  // ============================================================================

  logComplaintEvent(
    complaintId: string,
    event: string,
    wardId?: string,
    metadata?: Record<string, unknown>
  ): void {
    this.info(`Complaint event: ${event}`, {
      complaintId,
      event,
      wardId,
      ...metadata,
    });
  }

  logHousingMatch(
    userId: string,
    matchesCount: number,
    topScore: number,
    metadata?: Record<string, unknown>
  ): void {
    this.info(`Housing match completed`, {
      userId,
      matchesCount,
      topScore,
      ...metadata,
    });
  }

  logWardAnalysis(
    wardId: string,
    analysisType: string,
    duration: number,
    metadata?: Record<string, unknown>
  ): void {
    this.info(`Ward analysis completed`, {
      wardId,
      analysisType,
      duration,
      ...metadata,
    });
  }

  logNotification(
    type: string,
    recipientCount: number,
    successCount: number,
    metadata?: Record<string, unknown>
  ): void {
    this.info(`Notification broadcast completed`, {
      type,
      recipientCount,
      successCount,
      failureCount: recipientCount - successCount,
      ...metadata,
    });
  }

  logBotInteraction(
    sessionId: string,
    intent: string,
    responseTime: number,
    metadata?: Record<string, unknown>
  ): void {
    this.info(`Bot interaction completed`, {
      sessionId,
      intent,
      responseTime,
      ...metadata,
    });
  }

  // ============================================================================
  // Private Methods
  // ============================================================================

  private log(level: LogLevel, message: string, metadata?: Record<string, unknown>): void {
    const logEntry: ILogEntry = {
      level,
      message,
      timestamp: new Date(),
      service: this.serviceName,
      function: this.functionName,
      requestId: this.requestId,
      ...metadata,
    };

    // Extract common fields for better indexing
    const { userId, wardId, complaintId, duration, error, ...rest } = logEntry;

    // Log to Cloud Logging
    const cloudLogEntry = {
      severity: level.toUpperCase(),
      message: `[${this.serviceName}] ${message}`,
      requestId: this.requestId,
      service: this.serviceName,
      function: this.functionName,
      userId,
      wardId,
      complaintId,
      duration,
      error,
      metadata: rest,
    };

    // Use appropriate logger method based on level
    switch (level) {
      case LogLevel.DEBUG:
        cloudLogger.debug(cloudLogEntry);
        break;
      case LogLevel.INFO:
        cloudLogger.info(cloudLogEntry);
        break;
      case LogLevel.WARN:
        cloudLogger.warn(cloudLogEntry);
        break;
      case LogLevel.ERROR:
        cloudLogger.error(cloudLogEntry);
        break;
    }

    // Also log to console for local development
    if (process.env.NODE_ENV === 'development') {
      const consoleMessage = `${level.toUpperCase()} [${this.serviceName}] ${message}`;
      const consoleData = { requestId: this.requestId, ...metadata };
      
      switch (level) {
        case LogLevel.DEBUG:
          console.debug(consoleMessage, consoleData);
          break;
        case LogLevel.INFO:
          console.info(consoleMessage, consoleData);
          break;
        case LogLevel.WARN:
          console.warn(consoleMessage, consoleData);
          break;
        case LogLevel.ERROR:
          console.error(consoleMessage, consoleData);
          break;
      }
    }
  }

  private generateRequestId(): string {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

export function createLogger(serviceName: string, functionName?: string): Logger {
  return new Logger(serviceName, functionName);
}

export function createFunctionLogger(functionName: string): Logger {
  const serviceName = process.env.FUNCTION_NAME?.split('-')[0] || 'unknown';
  return new Logger(serviceName, functionName);
}

// ============================================================================
// Default Logger Instance
// ============================================================================

export const logger = new Logger('nivasai-services');

// ============================================================================
// Performance Monitoring Decorator
// ============================================================================

export function logPerformance<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  loggerInstance: Logger = logger
): T {
  return (async (...args: unknown[]) => {
    const endTimer = loggerInstance.startTimer(fn.name);
    try {
      const result = await fn(...args);
      endTimer();
      return result;
    } catch (error) {
      endTimer();
      loggerInstance.error(`Performance error in ${fn.name}`, error as Error);
      throw error;
    }
  }) as T;
}

// ============================================================================
// Error Context Enricher
// ============================================================================

export class ErrorContext {
  private context: Record<string, unknown> = {};

  static create(): ErrorContext {
    return new ErrorContext();
  }

  addUserId(userId: string): ErrorContext {
    this.context.userId = userId;
    return this;
  }

  addWardId(wardId: string): ErrorContext {
    this.context.wardId = wardId;
    return this;
  }

  addComplaintId(complaintId: string): ErrorContext {
    this.context.complaintId = complaintId;
    return this;
  }

  addRequestId(requestId: string): ErrorContext {
    this.context.requestId = requestId;
    return this;
  }

  addCustom(key: string, value: unknown): ErrorContext {
    this.context[key] = value;
    return this;
  }

  getContext(): Record<string, unknown> {
    return { ...this.context };
  }

  enrichError(error: Error): Error {
    const enrichedError = new Error(error.message);
    enrichedError.stack = error.stack;
    enrichedError.name = error.name;
    
    // Add context to error object for logging
    (enrichedError as any).context = this.getContext();
    
    return enrichedError;
  }
}

// ============================================================================
// Export Utilities
// ============================================================================

export function withErrorContext<T extends (...args: unknown[]) => unknown>(
  fn: T,
  contextBuilder: () => ErrorContext
): T {
  return ((...args: unknown[]) => {
    try {
      return fn(...args);
    } catch (error) {
      const context = contextBuilder();
      throw context.enrichError(error as Error);
    }
  }) as T;
}

export function createErrorContext(): ErrorContext {
  return ErrorContext.create();
}
