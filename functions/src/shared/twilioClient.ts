/**
 * Twilio REST Client wrapper for WhatsApp and FCM notifications
 */

import { Twilio } from 'twilio';
import { withTwilioRetry } from './retryHelper';
import { logger } from './logger';

// ============================================================================
// Twilio Client Class
// ============================================================================

export class TwilioClient {
  private readonly client: Twilio;
  private readonly whatsappFrom: string;

  constructor() {
    const accountSid = process.env.TWILIO_ACCOUNT_SID;
    const authToken = process.env.TWILIO_AUTH_TOKEN;
    const whatsappNumber = process.env.TWILIO_WHATSAPP_NUMBER;

    if (!accountSid || !authToken || !whatsappNumber) {
      throw new Error('Twilio credentials are required');
    }

    this.client = new Twilio(accountSid, authToken);
    this.whatsappFrom = whatsappNumber;
  }

  // ============================================================================
  // WhatsApp Messaging
  // ============================================================================

  async sendWhatsAppMessage(
    to: string,
    message: string,
    mediaUrl?: string[]
  ): Promise<{ messageId: string; status: string }> {
    return withTwilioRetry(async () => {
      try {
        logger.debug('Sending WhatsApp message', {
          to,
          messageLength: message.length,
          hasMedia: !!mediaUrl?.length,
        });

        const messageParams: any = {
          from: this.whatsappFrom,
          to: `whatsapp:${to}`,
          body: message,
        };

        if (mediaUrl && mediaUrl.length > 0) {
          messageParams.mediaUrl = mediaUrl;
        }

        const twilioMessage = await this.client.messages.create(messageParams);

        logger.info('WhatsApp message sent successfully', {
          messageId: twilioMessage.sid,
          to,
          status: twilioMessage.status,
        });

        return {
          messageId: twilioMessage.sid,
          status: twilioMessage.status,
        };
      } catch (error) {
        logger.error('Failed to send WhatsApp message', error as Error, {
          to,
        });
        throw error;
      }
    }, 'sendWhatsApp');
  }

  async sendWhatsAppTemplateMessage(
    to: string,
    templateName: string,
    templateParams?: string[]
  ): Promise<{ messageId: string; status: string }> {
    return withTwilioRetry(async () => {
      try {
        logger.debug('Sending WhatsApp template message', {
          to,
          templateName,
          paramCount: templateParams?.length || 0,
        });

        const messageParams = {
          from: this.whatsappFrom,
          to: `whatsapp:${to}`,
          contentSid: templateName,
          contentVariables: templateParams ? JSON.stringify(templateParams) : undefined,
        };

        const twilioMessage = await this.client.messages.create(messageParams);

        logger.info('WhatsApp template message sent successfully', {
          messageId: twilioMessage.sid,
          to,
          templateName,
          status: twilioMessage.status,
        });

        return {
          messageId: twilioMessage.sid,
          status: twilioMessage.status,
        };
      } catch (error) {
        logger.error('Failed to send WhatsApp template message', error as Error, {
          to,
          templateName,
        });
        throw error;
      }
    }, 'sendWhatsAppTemplate');
  }

  // ============================================================================
  // FCM Notifications (via Twilio Notify)
  // ============================================================================

  async sendFCMNotification(
    tokens: string[],
    notification: {
      title: string;
      body: string;
      data?: Record<string, string>;
    }
  ): Promise<{ successCount: number; failureCount: number; results: any[] }> {
    return withTwilioRetry(async () => {
      try {
        logger.debug('Sending FCM notification', {
          tokenCount: tokens.length,
          title: notification.title,
        });

        // Create a Twilio Notify service for FCM
        // Note: This assumes you have configured Twilio Notify with FCM
        const notifyServiceSid = process.env.TWILIO_NOTIFY_SERVICE_SID;
        
        if (!notifyServiceSid) {
          throw new Error('Twilio Notify service SID not configured');
        }

        const bindings = tokens.map(token => ({
          bindingType: 'fcm',
          address: token,
        }));

        const notificationPayload = {
          title: notification.title,
          body: notification.body,
          data: notification.data || {},
        };

        // Create notifications in batches of 500 (Twilio limit)
        const batchSize = 500;
        const results: any[] = [];
        let successCount = 0;
        let failureCount = 0;

        for (let i = 0; i < bindings.length; i += batchSize) {
          const batch = bindings.slice(i, i + batchSize);
          
          try {
            const notification = await this.client.notify.services(notifyServiceSid).notifications.create({
              identity: [], // Not using identity for FCM
              toBinding: batch,
              fcmNotification: notificationPayload,
            });

            // Process results
            if (notification.result) {
              Object.values(notification.result).forEach((result: any) => {
                results.push(result);
                if (result.status === 'sent') {
                  successCount++;
                } else {
                  failureCount++;
                }
              });
            }
          } catch (batchError) {
            logger.error('Failed to send FCM batch', batchError as Error, {
              batchSize: batch.length,
              batchIndex: Math.floor(i / batchSize),
            });
            failureCount += batch.length;
          }
        }

        logger.info('FCM notification sent', {
          totalTokens: tokens.length,
          successCount,
          failureCount,
        });

        return {
          successCount,
          failureCount,
          results,
        };
      } catch (error) {
        logger.error('Failed to send FCM notification', error as Error, {
          tokenCount: tokens.length,
        });
        throw error;
      }
    }, 'sendFCM');
  }

  // ============================================================================
  // SMS Messaging (for fallback)
  // ============================================================================

  async sendSMS(
    to: string,
    message: string
  ): Promise<{ messageId: string; status: string }> {
    return withTwilioRetry(async () => {
      try {
        logger.debug('Sending SMS message', {
          to,
          messageLength: message.length,
        });

        const twilioMessage = await this.client.messages.create({
          from: process.env.TWILIO_PHONE_NUMBER,
          to,
          body: message,
        });

        logger.info('SMS message sent successfully', {
          messageId: twilioMessage.sid,
          to,
          status: twilioMessage.status,
        });

        return {
          messageId: twilioMessage.sid,
          status: twilioMessage.status,
        };
      } catch (error) {
        logger.error('Failed to send SMS message', error as Error, {
          to,
        });
        throw error;
      }
    }, 'sendSMS');
  }

  // ============================================================================
  // Message Status Tracking
  // ============================================================================

  async getMessageStatus(messageId: string): Promise<{
    sid: string;
    status: string;
    errorCode?: string;
    errorMessage?: string;
    dateCreated: Date;
    dateUpdated: Date;
  }> {
    try {
      const message = await this.client.messages(messageId).fetch();
      
      return {
        sid: message.sid,
        status: message.status,
        errorCode: message.errorMessage ? message.errorCode : undefined,
        errorMessage: message.errorMessage || undefined,
        dateCreated: message.dateCreated,
        dateUpdated: message.dateUpdated,
      };
    } catch (error) {
      logger.error('Failed to get message status', error as Error, {
        messageId,
      });
      throw error;
    }
  }

  async getMessagesByDateRange(
    dateFrom: Date,
    dateTo: Date,
    limit: number = 100
  ): Promise<Array<{
    sid: string;
    from: string;
    to: string;
    body: string;
    status: string;
    dateCreated: Date;
  }>> {
    try {
      const messages = await this.client.messages.list({
        dateSentAfter: dateFrom,
        dateSentBefore: dateTo,
        limit,
      });

      return messages.map(message => ({
        sid: message.sid,
        from: message.from,
        to: message.to,
        body: message.body,
        status: message.status,
        dateCreated: message.dateCreated,
      }));
    } catch (error) {
      logger.error('Failed to get messages by date range', error as Error, {
        dateFrom,
        dateTo,
        limit,
      });
      throw error;
    }
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  formatPhoneNumber(phoneNumber: string): string {
    // Format phone number for Twilio (E.164 format)
    if (phoneNumber.startsWith('+')) {
      return phoneNumber;
    }
    
    // Remove any non-digit characters
    const cleaned = phoneNumber.replace(/\D/g, '');
    
    // Add country code for Indian numbers
    if (cleaned.length === 10) {
      return `+91${cleaned}`;
    }
    
    return phoneNumber;
  }

  isValidPhoneNumber(phoneNumber: string): boolean {
    try {
      // Use Twilio's validation
      const formatted = this.formatPhoneNumber(phoneNumber);
      return /^\+\d{10,15}$/.test(formatted);
    } catch {
      return false;
    }
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  async healthCheck(): Promise<boolean> {
    try {
      // Try to fetch account info as a health check
      await this.client.api.accounts(this.client.accountSid).fetch();
      return true;
    } catch (error) {
      logger.error('Twilio health check failed', error as Error);
      return false;
    }
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const twilioClient = new TwilioClient();
