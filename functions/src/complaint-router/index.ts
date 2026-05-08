/**
 * Complaint Router Service
 * 
 * Trigger: Pub/Sub topic "complaint-classified"
 * 
 * Routes classified complaints to appropriate ward officers and sends notifications
 * via WhatsApp and FCM.
 */

import { onMessagePublished } from 'firebase-functions/v2/pubsub';
import { logger } from '../shared/logger';
import { firestoreAdmin } from '../shared/firestoreAdmin';
import { twilioClient } from '../shared/twilioClient';
import { bigqueryClient } from '../shared/bigqueryClient';
import { IComplaint, IGeminiClassification, IComplaintEvent } from '../shared/types';

// ============================================================================
// Main Function
// ============================================================================

export const routeComplaint = onMessagePublished(
  {
    topic: 'complaint-classified',
    region: 'asia-south1',
  },
  async (event) => {
    const loggerInstance = logger;
    const endTimer = loggerInstance.startTimer('route-complaint');
    
    try {
      const messageData = event.data.message.json as {
        complaintId: string;
        classification: IGeminiClassification;
      };

      const { complaintId, classification } = messageData;

      loggerInstance.logFunctionStart({
        complaintId,
        category: classification.category,
        severity: classification.severity,
        suggestedDepartment: classification.suggestedDepartment,
      });

      // Get complaint details
      const complaint = await firestoreAdmin.getComplaint(complaintId);
      if (!complaint) {
        throw new Error(`Complaint ${complaintId} not found`);
      }

      // Find assigned officer for the ward
      const wardOfficer = await findWardOfficer(complaint.wardId);
      if (!wardOfficer) {
        loggerInstance.warn('No officer assigned to ward', {
          complaintId,
          wardId: complaint.wardId,
        });
        await updateComplaintAsUnassigned(complaintId);
        return;
      }

      // Send WhatsApp notification
      const whatsappResult = await sendWhatsAppNotification(
        wardOfficer.phoneNumber,
        complaint,
        classification
      );

      // Send FCM notification
      const fcmResult = await sendFCMNotification(
        wardOfficer.userId,
        complaint,
        classification
      );

      // Update complaint with routing information
      await updateComplaintWithRouting(
        complaintId,
        wardOfficer.userId,
        whatsappResult.success,
        fcmResult.success
      );

      // Log routing event to BigQuery
      await logComplaintEvent(complaintId, 'routed', {
        wardId: complaint.wardId,
        routedTo: wardOfficer.userId,
        whatsappSent: whatsappResult.success,
        fcmSent: fcmResult.success,
        category: classification.category,
        severity: classification.severity,
      });

      loggerInstance.logFunctionEnd({
        complaintId,
        routedTo: wardOfficer.userId,
        whatsappSent: whatsappResult.success,
        fcmSent: fcmResult.success,
      });

    } catch (error) {
      loggerInstance.logFunctionError(error as Error, {
        messageId: event.data.messageId,
      });
      throw error;
    } finally {
      endTimer();
    }
  }
);

// ============================================================================
// Helper Functions
// ============================================================================

async function findWardOfficer(wardId: string): Promise<{
  userId: string;
  phoneNumber: string;
  name: string;
} | null> {
  try {
    // Query wardOfficers collection for the specified ward
    const officers = await firestoreAdmin.queryCollection<any>(
      'wardOfficers',
      [{ field: 'wardId', operator: '==', value: wardId }],
      undefined,
      1
    );

    if (officers.length === 0) {
      return null;
    }

    const officer = officers[0];
    return {
      userId: officer.userId,
      phoneNumber: officer.phoneNumber,
      name: officer.name,
    };
  } catch (error) {
    logger.error('Failed to find ward officer', error as Error, { wardId });
    return null;
  }
}

async function sendWhatsAppNotification(
  phoneNumber: string,
  complaint: IComplaint,
  classification: IGeminiClassification
): Promise<{ success: boolean; messageId?: string; error?: string }> {
  try {
    const message = `New complaint in Ward ${complaint.wardId}: ${classification.category} (Severity: ${classification.severity}).\n\nLocation: ${complaint.location.address}\n\nDescription: ${complaint.description.substring(0, 100)}...\n\nView: https://nivasai.web.app/complaints/${complaint.id}`;

    const result = await twilioClient.sendWhatsAppMessage(phoneNumber, message);

    logger.info('WhatsApp notification sent successfully', {
      complaintId: complaint.id,
      phoneNumber,
      messageId: result.messageId,
    });

    return { success: true, messageId: result.messageId };
  } catch (error) {
    logger.error('Failed to send WhatsApp notification', error as Error, {
      complaintId: complaint.id,
      phoneNumber,
    });

    return {
      success: false,
      error: (error as Error).message,
    };
  }
}

async function sendFCMNotification(
  officerUserId: string,
  complaint: IComplaint,
  classification: IGeminiClassification
): Promise<{ success: boolean; successCount?: number; error?: string }> {
  try {
    // Get FCM tokens for the officer
    const tokens = await firestoreAdmin.getUserFCMTokens(officerUserId);
    
    if (tokens.length === 0) {
      logger.warn('No FCM tokens found for officer', {
        officerUserId,
        complaintId: complaint.id,
      });
      return { success: false, error: 'No FCM tokens available' };
    }

    const notificationPayload = {
      title: `New ${classification.category} Complaint`,
      body: `Severity: ${classification.severity} - ${complaint.location.address}`,
      data: {
        complaintId: complaint.id,
        wardId: complaint.wardId,
        category: classification.category,
        severity: classification.severity,
        type: 'new_complaint',
      },
    };

    // Send multicast FCM notification
    const result = await twilioClient.sendFCMNotification(
      tokens.map(t => t.token),
      notificationPayload
    );

    logger.info('FCM notification sent successfully', {
      complaintId: complaint.id,
      officerUserId,
      tokenCount: tokens.length,
      successCount: result.successCount,
      failureCount: result.failureCount,
    });

    return { success: true, successCount: result.successCount };
  } catch (error) {
    logger.error('Failed to send FCM notification', error as Error, {
      officerUserId,
      complaintId: complaint.id,
    });

    return {
      success: false,
      error: (error as Error).message,
    };
  }
}

async function updateComplaintWithRouting(
  complaintId: string,
  routedTo: string,
  whatsappSent: boolean,
  fcmSent: boolean
): Promise<void> {
  try {
    await firestoreAdmin.updateComplaint(complaintId, {
      routedTo,
      routedAt: new Date(),
      notificationSent: whatsappSent || fcmSent,
      status: 'in_progress', // Move to in_progress once routed
    });

    logger.info('Complaint updated with routing information', {
      complaintId,
      routedTo,
      whatsappSent,
      fcmSent,
    });
  } catch (error) {
    logger.error('Failed to update complaint with routing', error as Error, {
      complaintId,
    });
    throw error;
  }
}

async function updateComplaintAsUnassigned(complaintId: string): Promise<void> {
  try {
    await firestoreAdmin.updateComplaint(complaintId, {
      status: 'escalated', // Escalate since no officer is assigned
      geminiSummary: 'No officer assigned to this ward - complaint escalated',
      updatedAt: new Date(),
    });

    logger.info('Complaint marked as escalated (no officer assigned)', {
      complaintId,
    });
  } catch (error) {
    logger.error('Failed to update complaint as unassigned', error as Error, {
      complaintId,
    });
    throw error;
  }
}

async function logComplaintEvent(
  complaintId: string,
  event: string,
  data: Record<string, unknown>
): Promise<void> {
  try {
    const complaintEvent: IComplaintEvent = {
      complaintId,
      wardId: data.wardId as string,
      event: event as any,
      timestamp: new Date(),
      data,
    };

    await bigqueryClient.insertComplaintEvent(complaintEvent);

    logger.info('Complaint event logged to BigQuery', {
      complaintId,
      event,
    });
  } catch (error) {
    logger.error('Failed to log complaint event to BigQuery', error as Error, {
      complaintId,
      event,
    });
    // Don't throw here - logging failure shouldn't break the main flow
  }
}

// ============================================================================
// Manual Routing Function (for admin use)
// ============================================================================

export const manualRouteComplaint = onRequest(
  {
    region: 'asia-south1',
  },
  async (req, res) => {
    const loggerInstance = logger;
    
    try {
      if (req.method !== 'POST') {
        res.status(405).json({ error: 'Method not allowed' });
        return;
      }

      const { complaintId, officerId } = req.body;

      if (!complaintId || !officerId) {
        res.status(400).json({ error: 'complaintId and officerId are required' });
        return;
      }

      loggerInstance.info('Manual complaint routing requested', {
        complaintId,
        officerId,
      });

      // Get complaint details
      const complaint = await firestoreAdmin.getComplaint(complaintId);
      if (!complaint) {
        res.status(404).json({ error: 'Complaint not found' });
        return;
      }

      // Get officer details
      const officers = await firestoreAdmin.queryCollection<any>(
        'wardOfficers',
        [{ field: 'userId', operator: '==', value: officerId }],
        undefined,
        1
      );

      if (officers.length === 0) {
        res.status(404).json({ error: 'Officer not found' });
        return;
      }

      const officer = officers[0];

      // Send notifications
      const whatsappResult = await sendWhatsAppNotification(
        officer.phoneNumber,
        complaint,
        {
          category: complaint.category || 'other',
          severity: complaint.severity || 'medium',
          summary: complaint.geminiSummary || 'Manual routing',
          suggestedDepartment: complaint.suggestedDepartment || 'municipal',
          confidence: 1.0,
        }
      );

      const fcmResult = await sendFCMNotification(
        officer.userId,
        complaint,
        {
          category: complaint.category || 'other',
          severity: complaint.severity || 'medium',
          summary: complaint.geminiSummary || 'Manual routing',
          suggestedDepartment: complaint.suggestedDepartment || 'municipal',
          confidence: 1.0,
        }
      );

      // Update complaint
      await updateComplaintWithRouting(complaintId, officerId, whatsappResult.success, fcmResult.success);

      // Log event
      await logComplaintEvent(complaintId, 'routed', {
        wardId: complaint.wardId,
        routedTo: officerId,
        manual: true,
        whatsappSent: whatsappResult.success,
        fcmSent: fcmResult.success,
      });

      res.json({
        success: true,
        routedTo: officerId,
        whatsappSent: whatsappResult.success,
        fcmSent: fcmResult.success,
      });

    } catch (error) {
      loggerInstance.error('Manual complaint routing failed', error as Error);
      res.status(500).json({ error: (error as Error).message });
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
      const twilioHealthy = await twilioClient.healthCheck();
      const bigqueryHealthy = await bigqueryClient.healthCheck();

      const isHealthy = firestoreHealthy && twilioHealthy && bigqueryHealthy;

      const healthData = {
        status: isHealthy ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString(),
        services: {
          firestore: firestoreHealthy ? 'healthy' : 'unhealthy',
          twilio: twilioHealthy ? 'healthy' : 'unhealthy',
          bigquery: bigqueryHealthy ? 'healthy' : 'unhealthy',
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
