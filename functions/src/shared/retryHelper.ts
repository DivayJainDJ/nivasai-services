/**
 * Retry helper with exponential backoff for external API calls
 */

import { logger } from './logger';

// ============================================================================
// Configuration
// ============================================================================

interface IRetryConfig {
  readonly maxRetries: number;
  readonly baseDelayMs: number;
  readonly maxDelayMs: number;
  readonly backoffMultiplier: number;
  readonly jitter: boolean;
}

const DEFAULT_CONFIG: IRetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  backoffMultiplier: 2,
  jitter: true,
};

// ============================================================================
// Error Types
// ============================================================================

export class RetryableError extends Error {
  readonly retryable = true;
  readonly originalError: Error;

  constructor(message: string, originalError: Error) {
    super(message);
    this.name = 'RetryableError';
    this.originalError = originalError;
  }
}

export class NonRetryableError extends Error {
  readonly retryable = false;
  readonly originalError: Error;

  constructor(message: string, originalError: Error) {
    super(message);
    this.name = 'NonRetryableError';
    this.originalError = originalError;
  }
}

// ============================================================================
// Retry Function
// ============================================================================

export async function withRetry<T>(
  operation: () => Promise<T>,
  config: Partial<IRetryConfig> = {},
  context?: string
): Promise<T> {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  let lastError: Error;

  for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
    try {
      if (attempt > 0) {
        const delay = calculateDelay(attempt, finalConfig);
        logger.info(`Retrying operation${context ? ` (${context})` :}`, {
          attempt,
          maxRetries: finalConfig.maxRetries,
          delayMs: delay,
          error: lastError?.message,
        });
        await sleep(delay);
      }

      const result = await operation();
      
      if (attempt > 0) {
        logger.info(`Operation succeeded after ${attempt} retries${context ? ` (${context})` : ''}`);
      }
      
      return result;
    } catch (error) {
      lastError = error as Error;
      
      // Check if error is retryable
      if (!isRetryableError(lastError)) {
        logger.error(`Non-retryable error encountered${context ? ` (${context})` : ''}`, {
          error: lastError.message,
          stack: lastError.stack,
        });
        throw lastError;
      }

      if (attempt === finalConfig.maxRetries) {
        logger.error(`Max retries exceeded${context ? ` (${context})` : ''}`, {
          maxRetries: finalConfig.maxRetries,
          finalError: lastError.message,
        });
        throw new RetryableError(
          `Operation failed after ${finalConfig.maxRetries} retries: ${lastError.message}`,
          lastError
        );
      }

      logger.warn(`Operation failed, will retry${context ? ` (${context})` : ''}`, {
        attempt,
        error: lastError.message,
      });
    }
  }

  // This should never be reached, but TypeScript requires it
  throw lastError!;
}

// ============================================================================
// Helper Functions
// ============================================================================

function calculateDelay(attempt: number, config: IRetryConfig): number {
  let delay = config.baseDelayMs * Math.pow(config.backoffMultiplier, attempt - 1);
  
  // Apply maximum delay limit
  delay = Math.min(delay, config.maxDelayMs);
  
  // Add jitter to prevent thundering herd
  if (config.jitter) {
    delay = delay * (0.5 + Math.random() * 0.5);
  }
  
  return Math.floor(delay);
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isRetryableError(error: Error): boolean {
  // Check if it's our custom error type
  if (error instanceof RetryableError) return true;
  if (error instanceof NonRetryableError) return false;
  
  // Check common HTTP status codes that are retryable
  if ('status' in error) {
    const status = (error as any).status;
    // Retry on 5xx errors, 429 (Too Many Requests), and 408 (Request Timeout)
    return status >= 500 || status === 429 || status === 408;
  }
  
  // Check common network error messages
  const message = error.message.toLowerCase();
  const retryablePatterns = [
    'timeout',
    'network',
    'connection',
    'rate limit',
    'temporary',
    'service unavailable',
    'internal server error',
  ];
  
  return retryablePatterns.some(pattern => message.includes(pattern));
}

// ============================================================================
// Specialized Retry Wrappers
// ============================================================================

export async function withGeminiRetry<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<T> {
  return withRetry(operation, {
    maxRetries: 3,
    baseDelayMs: 2000,
    maxDelayMs: 10000,
  }, `gemini-${context}`);
}

export async function withMapsRetry<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<T> {
  return withRetry(operation, {
    maxRetries: 3,
    baseDelayMs: 1500,
    maxDelayMs: 8000,
  }, `maps-${context}`);
}

export async function withTwilioRetry<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<T> {
  return withRetry(operation, {
    maxRetries: 5,
    baseDelayMs: 1000,
    maxDelayMs: 15000,
  }, `twilio-${context}`);
}

export async function withDocumentAIRetry<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<T> {
  return withRetry(operation, {
    maxRetries: 2,
    baseDelayMs: 3000,
    maxDelayMs: 12000,
  }, `documentai-${context}`);
}

export async function withBigQueryRetry<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<T> {
  return withRetry(operation, {
    maxRetries: 5,
    baseDelayMs: 500,
    maxDelayMs: 5000,
  }, `bigquery-${context}`);
}

export async function withStorageRetry<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<T> {
  return withRetry(operation, {
    maxRetries: 3,
    baseDelayMs: 1000,
    maxDelayMs: 6000,
  }, `storage-${context}`);
}

// ============================================================================
// Batch Retry for Multiple Operations
// ============================================================================

export async function withBatchRetry<T>(
  operations: Array<() => Promise<T>>,
  config: Partial<IRetryConfig> = {},
  context?: string
): Promise<Array<{ success: boolean; result?: T; error?: Error }>> {
  const results = await Promise.allSettled(
    operations.map((op, index) => 
      withRetry(op, config, `${context}-batch-${index}`)
    )
  );

  return results.map((result, index) => {
    if (result.status === 'fulfilled') {
      return { success: true, result: result.value };
    } else {
      return { success: false, error: result.reason };
    }
  });
}

// ============================================================================
// Circuit Breaker Pattern
// ============================================================================

interface ICircuitBreakerConfig {
  readonly failureThreshold: number;
  readonly recoveryTimeoutMs: number;
  readonly monitoringPeriodMs: number;
}

export class CircuitBreaker {
  private failures = 0;
  private lastFailureTime?: Date;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(private config: ICircuitBreakerConfig) {}

  async execute<T>(operation: () => Promise<T>, context?: string): Promise<T> {
    if (this.state === 'open') {
      if (this.shouldAttemptReset()) {
        this.state = 'half-open';
        logger.info(`Circuit breaker half-open${context ? ` (${context})` : ''}`);
      } else {
        throw new Error('Circuit breaker is open');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failures = 0;
    this.state = 'closed';
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = new Date();

    if (this.failures >= this.config.failureThreshold) {
      this.state = 'open';
      logger.warn('Circuit breaker opened', {
        failures: this.failures,
        threshold: this.config.failureThreshold,
      });
    }
  }

  private shouldAttemptReset(): boolean {
    return this.lastFailureTime !== undefined &&
           Date.now() - this.lastFailureTime.getTime() >= this.config.recoveryTimeoutMs;
  }

  getState(): string {
    return this.state;
  }

  getFailures(): number {
    return this.failures;
  }
}

// ============================================================================
// Export Utility Functions
// ============================================================================

export function createRetryableError(message: string, originalError: Error): RetryableError {
  return new RetryableError(message, originalError);
}

export function createNonRetryableError(message: string, originalError: Error): NonRetryableError {
  return new NonRetryableError(message, originalError);
}

export function isRetryable(error: Error): boolean {
  return isRetryableError(error);
}
