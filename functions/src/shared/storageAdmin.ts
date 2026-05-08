/**
 * Cloud Storage Admin SDK wrapper for file operations
 */

import { getStorage, Storage } from 'firebase-admin/storage';
import { withStorageRetry } from './retryHelper';
import { logger } from './logger';

// ============================================================================
// Storage Admin Client
// ============================================================================

export class StorageAdminClient {
  private readonly storage: Storage;

  constructor() {
    this.storage = getStorage();
  }

  // ============================================================================
  // File Operations
  // ============================================================================

  async downloadFileAsBuffer(filePath: string): Promise<Buffer> {
    return withStorageRetry(async () => {
      try {
        logger.debug('Downloading file from storage', { filePath });
        
        const bucket = this.storage.bucket();
        const file = bucket.file(filePath);
        const [buffer] = await file.download();
        
        logger.info('File downloaded successfully', { 
          filePath, 
          size: buffer.length 
        });
        
        return buffer;
      } catch (error) {
        logger.error(`Failed to download file ${filePath}`, error as Error);
        throw error;
      }
    }, 'downloadFile');
  }

  async downloadFileAsBase64(filePath: string): Promise<string> {
    const buffer = await this.downloadFileAsBuffer(filePath);
    return buffer.toString('base64');
  }

  async uploadFile(
    filePath: string,
    buffer: Buffer,
    metadata?: {
      contentType?: string;
      metadata?: Record<string, string>;
    }
  ): Promise<void> {
    return withStorageRetry(async () => {
      try {
        logger.debug('Uploading file to storage', { 
          filePath, 
          size: buffer.length,
          contentType: metadata?.contentType 
        });
        
        const bucket = this.storage.bucket();
        const file = bucket.file(filePath);
        
        await file.save(buffer, {
          metadata: {
            contentType: metadata?.contentType || 'application/octet-stream',
            ...metadata?.metadata,
          },
        });
        
        logger.info('File uploaded successfully', { 
          filePath, 
          size: buffer.length 
        });
      } catch (error) {
        logger.error(`Failed to upload file ${filePath}`, error as Error);
        throw error;
      }
    }, 'uploadFile');
  }

  async deleteFile(filePath: string): Promise<void> {
    return withStorageRetry(async () => {
      try {
        logger.debug('Deleting file from storage', { filePath });
        
        const bucket = this.storage.bucket();
        const file = bucket.file(filePath);
        await file.delete();
        
        logger.info('File deleted successfully', { filePath });
      } catch (error) {
        logger.error(`Failed to delete file ${filePath}`, error as Error);
        throw error;
      }
    }, 'deleteFile');
  }

  async fileExists(filePath: string): Promise<boolean> {
    try {
      const bucket = this.storage.bucket();
      const file = bucket.file(filePath);
      const [exists] = await file.exists();
      return exists;
    } catch (error) {
      logger.error(`Failed to check file existence ${filePath}`, error as Error);
      return false;
    }
  }

  async getFileInfo(filePath: string): Promise<{
    size: number;
    contentType?: string;
    timeCreated: Date;
    updated: Date;
    md5Hash?: string;
  }> {
    try {
      const bucket = this.storage.bucket();
      const file = bucket.file(filePath);
      const [metadata] = await file.getMetadata();
      
      return {
        size: parseInt(metadata.size || '0'),
        contentType: metadata.contentType,
        timeCreated: new Date(metadata.timeCreated || ''),
        updated: new Date(metadata.updated || ''),
        md5Hash: metadata.md5Hash,
      };
    } catch (error) {
      logger.error(`Failed to get file info ${filePath}`, error as Error);
      throw error;
    }
  }

  // ============================================================================
  // Batch Operations
  // ============================================================================

  async deleteFiles(filePaths: string[]): Promise<void> {
    const bucket = this.storage.bucket();
    const promises = filePaths.map(async (filePath) => {
      try {
        const file = bucket.file(filePath);
        await file.delete();
        logger.debug('File deleted in batch', { filePath });
      } catch (error) {
        logger.error(`Failed to delete file in batch ${filePath}`, error as Error);
      }
    });
    
    await Promise.all(promises);
    logger.info('Batch file deletion completed', { 
      totalFiles: filePaths.length 
    });
  }

  // ============================================================================
  // Specialized Operations
  // ============================================================================

  async downloadComplaintPhoto(photoUrl: string): Promise<Buffer> {
    // Extract file path from URL
    const filePath = this.extractFilePathFromUrl(photoUrl);
    return this.downloadFileAsBuffer(filePath);
  }

  async downloadComplaintPhotoAsBase64(photoUrl: string): Promise<string> {
    const buffer = await this.downloadComplaintPhoto(photoUrl);
    return buffer.toString('base64');
  }

  async downloadDocument(documentUrl: string): Promise<Buffer> {
    const filePath = this.extractFilePathFromUrl(documentUrl);
    return this.downloadFileAsBuffer(filePath);
  }

  async downloadDocumentAsBase64(documentUrl: string): Promise<string> {
    const buffer = await this.downloadDocument(documentUrl);
    return buffer.toString('base64');
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  private extractFilePathFromUrl(url: string): string {
    try {
      // Extract path from Firebase Storage URL
      // Format: https://firebasestorage.googleapis.com/v0/b/BUCKET/o/PATH?alt=media
      const urlObj = new URL(url);
      const pathPart = urlObj.pathname.split('/o/')[1];
      
      if (!pathPart) {
        throw new Error('Invalid Firebase Storage URL format');
      }
      
      // Decode URL-encoded path
      return decodeURIComponent(pathPart.split('?')[0]);
    } catch (error) {
      logger.error('Failed to extract file path from URL', error as Error, { url });
      throw new Error('Invalid Firebase Storage URL');
    }
  }

  generatePublicUrl(filePath: string): string {
    const bucket = this.storage.bucket();
    const file = bucket.file(filePath);
    return file.publicUrl();
  }

  async getSignedUrl(
    filePath: string,
    options: {
      action: 'read' | 'write' | 'delete';
      expires: number; // in minutes
    }
  ): Promise<string> {
    try {
      const bucket = this.storage.bucket();
      const file = bucket.file(filePath);
      
      const config = {
        action: options.action,
        expires: Date.now() + (options.expires * 60 * 1000),
      };
      
      const [url] = await file.getSignedUrl(config);
      return url;
    } catch (error) {
      logger.error(`Failed to generate signed URL for ${filePath}`, error as Error);
      throw error;
    }
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  async healthCheck(): Promise<boolean> {
    try {
      const bucket = this.storage.bucket();
      await bucket.getMetadata();
      return true;
    } catch (error) {
      logger.error('Storage health check failed', error as Error);
      return false;
    }
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const storageAdmin = new StorageAdminClient();
