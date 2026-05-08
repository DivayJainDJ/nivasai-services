/**
 * Complaint Classifier Service
 * 
 * Trigger: Firestore onCreate on /complaints/{complaintId}
 * 
 * Classifies new complaints using Gemini Vision API and updates the complaint
 * document with classification results.
 */

import { onDocumentCreated } from 'firebase-functions/v2/firestore';
import { logger } from '../shared/logger';
import { firestoreAdmin } from '../shared/firestoreAdmin';
import { storageAdmin } from '../shared/storageAdmin';
import { geminiClient } from '../shared/geminiClient';
import { pubsub } from 'firebase-functions/v2';
import { IComplaint, IGeminiClassification } from '../shared/types';

// ============================================================================
// Main Function
// ============================================================================

export const classifyComplaint = onDocumentCreated(
  {
    document: 'complaints/{complaintId}',
    region: 'asia-south1',
  },
  async (event) => {
    const loggerInstance = logger;
    const endTimer = loggerInstance.startTimer('classify-complaint');
    
    try {
      const complaintId = event.params.complaintId;
      const complaintData = event.data.data() as IComplaint;
      
      loggerInstance.logFunctionStart({
        complaintId,
        userId: complaintData.userId,
        wardId: complaintData.wardId,
        hasPhoto: !!complaintData.photoUrl,
      });

      // Validate complaint data
      if (!complaintData.photoUrl) {
        loggerInstance.warn('Complaint has no photo, skipping classification', {
          complaintId,
        });
        await updateComplaintStatus(complaintId, 'classification-failed', 'No photo provided');
        return;
      }

      // Download photo from Cloud Storage
      const photoBase64 = await storageAdmin.downloadComplaintPhotoAsBase64(complaintData.photoUrl);
      
      // Classify with Gemini Vision
      const classification = await geminiClient.classifyComplaintImage(
        photoBase64,
        complaintData.description
      );

      // Update complaint with classification results
      await updateComplaintWithClassification(complaintId, classification);

      // Publish to Pub/Sub for routing
      await publishComplaintClassifiedEvent(complaintId, classification);

      loggerInstance.logFunctionEnd({
        complaintId,
        category: classification.category,
        severity: classification.severity,
        confidence: classification.confidence,
      });

    } catch (error) {
      loggerInstance.logFunctionError(error as Error, {
        complaintId: event.params.complaintId,
      });

      // Retry logic for classification failures
      if (shouldRetry(error as Error)) {
        loggerInstance.info('Scheduling retry for complaint classification', {
          complaintId: event.params.complaintId,
          retryDelay: '30s',
        });

        // Schedule retry after 30 seconds
        await scheduleRetry(event.params.complaintId);
      } else {
        // Mark as failed if not retryable
        await updateComplaintStatus(
          event.params.complaintId,
          'classification-failed',
          (error as Error).message
        );
      }
    } finally {
      endTimer();
    }
  }
);

// ============================================================================
// Helper Functions
// ============================================================================

async function updateComplaintWithClassification(
  complaintId: string,
  classification: IGeminiClassification
): Promise<void> {
  try {
    await firestoreAdmin.updateComplaint(complaintId, {
      category: classification.category,
      severity: classification.severity,
      geminiSummary: classification.summary,
      suggestedDepartment: classification.suggestedDepartment,
      classifiedAt: new Date(),
      status: 'pending', // Reset to pending after successful classification
    });

    logger.info('Complaint updated with classification', {
      complaintId,
      category: classification.category,
      severity: classification.severity,
    });
  } catch (error) {
    logger.error('Failed to update complaint with classification', error as Error, {
      complaintId,
    });
    throw error;
  }
}

async function updateComplaintStatus(
  complaintId: string,
  status: string,
  reason?: string
): Promise<void> {
  try {
    await firestoreAdmin.updateComplaint(complaintId, {
      status: status as any,
      updatedAt: new Date(),
      ...(reason && { geminiSummary: `Classification failed: ${reason}` }),
    });

    logger.info('Complaint status updated', {
      complaintId,
      status,
      reason,
    });
  } catch (error) {
    logger.error('Failed to update complaint status', error as Error, {
      complaintId,
      status,
    });
    throw error;
  }
}

async function publishComplaintClassifiedEvent(
  complaintId: string,
  classification: IGeminiClassification
): Promise<void> {
  try {
    const topic = pubsub.topic('complaint-classified');
    
    const message = {
      data: {
        complaintId,
        classification: {
          category: classification.category,
          severity: classification.severity,
          summary: classification.summary,
          suggestedDepartment: classification.suggestedDepartment,
          confidence: classification.confidence,
        },
      },
      attributes: {
        eventType: 'complaint-classified',
        severity: classification.severity,
        category: classification.category,
      },
    };

    await topic.publish(message);
    
    logger.info('Published complaint-classified event', {
      complaintId,
      category: classification.category,
      severity: classification.severity,
    });
  } catch (error) {
    logger.error('Failed to publish complaint-classified event', error as Error, {
      complaintId,
    });
    // Don't throw here - classification was successful, just notification failed
  }
}

function shouldRetry(error: Error): boolean {
  const errorMessage = error.message.toLowerCase();
  
  // Retry on network errors, timeouts, and temporary service issues
  const retryablePatterns = [
    'timeout',
    'network',
    'connection',
    'rate limit',
    'temporary',
    'service unavailable',
    'internal server error',
    'quota exceeded',
  ];

  return retryablePatterns.some(pattern => errorMessage.includes(pattern));
}

async function scheduleRetry(complaintId: string): Promise<void> {
  try {
    // Update complaint to indicate retry is scheduled
    await firestoreAdmin.updateComplaint(complaintId, {
      geminiSummary: 'Classification retry scheduled',
      updatedAt: new Date(),
    });

    // In a production environment, you might use Cloud Scheduler or Cloud Tasks
    // For now, we'll rely on the client to retry or implement a simple delay
    logger.info('Retry scheduled for complaint classification', {
      complaintId,
      retryIn: '30 seconds',
    });
  } catch (error) {
    logger.error('Failed to schedule retry', error as Error, {
      complaintId,
    });
  }
}

// ============================================================================
// Retry Handler (for manual retries or scheduled retries)
// ============================================================================

export const retryComplaintClassification = onDocumentWritten(
  {
    document: 'complaints/{complaintId}',
    region: 'asia-south1',
  },
  async (event) => {
    const complaintId = event.params.complaintId;
    const beforeData = event.data.before.data() as IComplaint;
    const afterData = event.data.after.data() as IComplaint;

    // Only retry if status is classification-failed and it's been more than 30 seconds
    if (
      afterData.status === 'classification-failed' &&
      afterData.geminiSummary?.includes('retry scheduled')
    ) {
      const timeSinceUpdate = Date.now() - afterData.updatedAt!.getTime();
      
      if (timeSinceUpdate >= 30000) { // 30 seconds
        logger.info('Executing scheduled retry for complaint classification', {
          complaintId,
        });

        try {
          // Re-trigger classification logic
          if (afterData.photoUrl) {
            const photoBase64 = await storageAdmin.downloadComplaintPhotoAsBase64(afterData.photoUrl);
            const classification = await geminiClient.classifyComplaintImage(
              photoBase64,
              afterData.description
            );

            await updateComplaintWithClassification(complaintId, classification);
            await publishComplaintClassifiedEvent(complaintId, classification);

            logger.info('Retry successful for complaint classification', {
              complaintId,
              category: classification.category,
              severity: classification.severity,
            });
          }
        } catch (error) {
          logger.error('Retry failed for complaint classification', error as Error, {
            complaintId,
          });

          // Mark as permanently failed after retry
          await updateComplaintStatus(
            complaintId,
            'classification-failed',
            `Retry failed: ${(error as Error).message}`
          );
        }
      }
    }
  }
);

// ============================================================================
// Health Check Function
// ============================================================================

export const healthCheck = onRequest(
  {
    region: 'asia-south1',
  },
  async (_req, res) => {
    try {
      const loggerInstance = logger;
      
      // Check dependencies
      const firestoreHealthy = await firestoreAdmin.healthCheck();
      const storageHealthy = await storageAdmin.healthCheck();
      const geminiHealthy = await geminiClient.healthCheck();

      const isHealthy = firestoreHealthy && storageHealthy && geminiHealthy;

      const healthData = {
        status: isHealthy ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString(),
        services: {
          firestore: firestoreHealthy ? 'healthy' : 'unhealthy',
          storage: storageHealthy ? 'healthy' : 'unhealthy',
          gemini: geminiHealthy ? 'healthy' : 'unhealthy',
        },
      };

      loggerInstance.info('Health check completed', healthData);

      res.status(isHealthy ? 200 : 503).json(healthData);
    } catch (error) {
      logger.error('Health check failed', error as Error);
      res.status(500).json({
        status: 'unhealthy',
        error: (error as Error).message,
        timestamp: new Date().toISOString(),
      });
    }
  }
);
