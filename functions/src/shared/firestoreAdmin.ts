/**
 * Firestore Admin SDK wrapper with batch operations and utilities
 */

import { getFirestore, Firestore, WriteBatch, DocumentReference } from 'firebase-admin/firestore';
import { logger } from './logger';
import { IComplaint, IFamilyProfile, IHousingUnit, IWard } from './types';

// ============================================================================
// Firestore Admin Client
// ============================================================================

export class FirestoreAdminClient {
  private readonly db: Firestore;

  constructor() {
    this.db = getFirestore();
  }

  // ============================================================================
  // Document Operations
  // ============================================================================

  async getDocument<T>(collection: string, docId: string): Promise<T | null> {
    try {
      const docRef = this.db.collection(collection).doc(docId);
      const docSnap = await docRef.get();
      
      if (!docSnap.exists) {
        return null;
      }
      
      return { id: docSnap.id, ...docSnap.data() } as T;
    } catch (error) {
      logger.error(`Failed to get document ${collection}/${docId}`, error as Error);
      throw error;
    }
  }

  async createDocument<T>(collection: string, data: Omit<T, 'id'>): Promise<T> {
    try {
      const docRef = await this.db.collection(collection).add({
        ...data,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
      
      const newDoc = await docRef.get();
      return { id: newDoc.id, ...newDoc.data() } as T;
    } catch (error) {
      logger.error(`Failed to create document in ${collection}`, error as Error);
      throw error;
    }
  }

  async updateDocument<T>(
    collection: string, 
    docId: string, 
    data: Partial<T>
  ): Promise<void> {
    try {
      const docRef = this.db.collection(collection).doc(docId);
      await docRef.update({
        ...data,
        updatedAt: new Date(),
      });
    } catch (error) {
      logger.error(`Failed to update document ${collection}/${docId}`, error as Error);
      throw error;
    }
  }

  async deleteDocument(collection: string, docId: string): Promise<void> {
    try {
      const docRef = this.db.collection(collection).doc(docId);
      await docRef.delete();
    } catch (error) {
      logger.error(`Failed to delete document ${collection}/${docId}`, error as Error);
      throw error;
    }
  }

  // ============================================================================
  // Query Operations
  // ============================================================================

  async queryCollection<T>(
    collection: string,
    constraints: Array<{
      field: string;
      operator: '==' | '!=' | '>' | '>=' | '<' | '<=' | 'in' | 'array-contains' | 'array-contains-any';
      value: unknown;
    }> = [],
    orderBy?: { field: string; direction: 'asc' | 'desc' },
    limit?: number
  ): Promise<T[]> {
    try {
      let query = this.db.collection(collection) as any;
      
      // Apply where constraints
      for (const constraint of constraints) {
        query = query.where(constraint.field, constraint.operator, constraint.value);
      }
      
      // Apply ordering
      if (orderBy) {
        query = query.orderBy(orderBy.field, orderBy.direction);
      }
      
      // Apply limit
      if (limit) {
        query = query.limit(limit);
      }
      
      const querySnap = await query.get();
      return querySnap.docs.map(doc => ({ id: doc.id, ...doc.data() } as T));
    } catch (error) {
      logger.error(`Failed to query collection ${collection}`, error as Error);
      throw error;
    }
  }

  async queryCollectionGroup<T>(
    collectionGroup: string,
    constraints: Array<{
      field: string;
      operator: '==' | '!=' | '>' | '>=' | '<' | '<=' | 'in' | 'array-contains' | 'array-contains-any';
      value: unknown;
    }> = [],
    orderBy?: { field: string; direction: 'asc' | 'desc' },
    limit?: number
  ): Promise<T[]> {
    try {
      let query = this.db.collectionGroup(collectionGroup) as any;
      
      // Apply where constraints
      for (const constraint of constraints) {
        query = query.where(constraint.field, constraint.operator, constraint.value);
      }
      
      // Apply ordering
      if (orderBy) {
        query = query.orderBy(orderBy.field, orderBy.direction);
      }
      
      // Apply limit
      if (limit) {
        query = query.limit(limit);
      }
      
      const querySnap = await query.get();
      return querySnap.docs.map(doc => ({ id: doc.id, ...doc.data() } as T));
    } catch (error) {
      logger.error(`Failed to query collection group ${collectionGroup}`, error as Error);
      throw error;
    }
  }

  // ============================================================================
  // Batch Operations
  // ============================================================================

  createBatch(): WriteBatch {
    return this.db.batch();
  }

  async commitBatch(batch: WriteBatch): Promise<void> {
    try {
      await batch.commit();
      logger.info('Batch committed successfully');
    } catch (error) {
      logger.error('Failed to commit batch', error as Error);
      throw error;
    }
  }

  async batchUpdateDocuments<T>(
    updates: Array<{
      collection: string;
      docId: string;
      data: Partial<T>;
    }>
  ): Promise<void> {
    const batch = this.createBatch();
    
    for (const update of updates) {
      const docRef = this.db.collection(update.collection).doc(update.docId);
      batch.update(docRef, {
        ...update.data,
        updatedAt: new Date(),
      });
    }
    
    await this.commitBatch(batch);
  }

  async batchCreateDocuments<T>(
    creates: Array<{
      collection: string;
      data: Omit<T, 'id'>;
    }>
  ): Promise<T[]> {
    const batch = this.createBatch();
    const docRefs: DocumentReference[] = [];
    
    for (const create of creates) {
      const docRef = this.db.collection(create.collection).doc();
      docRefs.push(docRef);
      batch.set(docRef, {
        ...create.data,
        id: docRef.id,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
    
    await this.commitBatch(batch);
    
    // Fetch the created documents
    const results: T[] = [];
    for (const docRef of docRefs) {
      const docSnap = await docRef.get();
      results.push({ id: docSnap.id, ...docSnap.data() } as T);
    }
    
    return results;
  }

  // ============================================================================
  // Complaint Operations
  // ============================================================================

  async getComplaint(complaintId: string): Promise<IComplaint | null> {
    return this.getDocument<IComplaint>('complaints', complaintId);
  }

  async updateComplaint(
    complaintId: string, 
    updates: Partial<IComplaint>
  ): Promise<void> {
    return this.updateDocument('complaints', complaintId, updates);
  }

  async getComplaintsByWard(wardId: string, limit?: number): Promise<IComplaint[]> {
    return this.queryCollection<IComplaint>(
      'complaints',
      [{ field: 'wardId', operator: '==', value: wardId }],
      { field: 'createdAt', direction: 'desc' },
      limit
    );
  }

  async getComplaintsByUser(userId: string, limit?: number): Promise<IComplaint[]> {
    return this.queryCollection<IComplaint>(
      'complaints',
      [{ field: 'userId', operator: '==', value: userId }],
      { field: 'createdAt', direction: 'desc' },
      limit
    );
  }

  // ============================================================================
  // Housing Operations
  // ============================================================================

  async getFamilyProfile(userId: string): Promise<IFamilyProfile | null> {
    const profiles = await this.queryCollection<IFamilyProfile>(
      'familyProfiles',
      [{ field: 'userId', operator: '==', value: userId }],
      undefined,
      1
    );
    return profiles.length > 0 ? profiles[0] : null;
  }

  async updateFamilyProfile(
    profileId: string, 
    updates: Partial<IFamilyProfile>
  ): Promise<void> {
    return this.updateDocument('familyProfiles', profileId, updates);
  }

  async getAvailableHousingUnits(
    categories?: string[],
    limit?: number
  ): Promise<IHousingUnit[]> {
    const constraints = [{ field: 'status', operator: '==', value: 'available' }];
    
    if (categories && categories.length > 0) {
      constraints.push({
        field: 'eligibility.category',
        operator: 'array-contains-any',
        value: categories,
      });
    }
    
    return this.queryCollection<IHousingUnit>(
      'housingUnits',
      constraints,
      { field: 'createdAt', direction: 'desc' },
      limit
    );
  }

  // ============================================================================
  // Ward Operations
  // ============================================================================

  async getWard(wardId: string): Promise<IWard | null> {
    return this.getDocument<IWard>('wards', wardId);
  }

  async getAllWards(): Promise<IWard[]> {
    return this.queryCollection<IWard>('wards', [], { field: 'name', direction: 'asc' });
  }

  async updateWard(wardId: string, updates: Partial<IWard>): Promise<void> {
    return this.updateDocument('wards', wardId, updates);
  }

  // ============================================================================
  // User Token Operations (for FCM)
  // ============================================================================

  async getUserFCMTokens(userId: string): Promise<Array<{ token: string; role: string }>> {
    const tokens = await this.queryCollection<any>(
      'userTokens',
      [{ field: 'userId', operator: '==', value: userId }]
    );
    
    return tokens.map(token => ({
      token: token.token,
      role: token.role,
    }));
  }

  async getFCMTokensByRole(role: string): Promise<Array<{ userId: string; token: string }>> {
    const tokens = await this.queryCollection<any>(
      'userTokens',
      [{ field: 'role', operator: '==', value: role }]
    );
    
    return tokens.map(token => ({
      userId: token.userId,
      token: token.token,
    }));
  }

  async getFCMTokensByWard(
    wardId: string, 
    role?: string
  ): Promise<Array<{ userId: string; token: string }>> {
    const constraints = [{ field: 'wardId', operator: '==', value: wardId }];
    
    if (role) {
      constraints.push({ field: 'role', operator: '==', value: role });
    }
    
    const tokens = await this.queryCollection<any>('userTokens', constraints);
    
    return tokens.map(token => ({
      userId: token.userId,
      token: token.token,
    }));
  }

  // ============================================================================
  // Analytics Operations
  // ============================================================================

  async getComplaintStats(wardId?: string): Promise<{
    total: number;
    byStatus: Record<string, number>;
    byCategory: Record<string, number>;
    avgResolutionTime: number;
  }> {
    try {
      let constraints: any[] = [];
      
      if (wardId) {
        constraints.push({ field: 'wardId', operator: '==', value: wardId });
      }
      
      const complaints = await this.queryCollection<IComplaint>('complaints', constraints);
      
      const stats = {
        total: complaints.length,
        byStatus: {} as Record<string, number>,
        byCategory: {} as Record<string, number>,
        avgResolutionTime: 0,
      };
      
      // Calculate by status
      for (const complaint of complaints) {
        stats.byStatus[complaint.status] = (stats.byStatus[complaint.status] || 0) + 1;
        
        if (complaint.category) {
          stats.byCategory[complaint.category] = (stats.byCategory[complaint.category] || 0) + 1;
        }
      }
      
      // Calculate average resolution time
      const resolvedComplaints = complaints.filter(c => c.status === 'resolved' && c.updatedAt);
      if (resolvedComplaints.length > 0) {
        const totalTime = resolvedComplaints.reduce((sum, c) => {
          const createdAt = c.createdAt.getTime();
          const resolvedAt = c.updatedAt!.getTime();
          return sum + (resolvedAt - createdAt);
        }, 0);
        stats.avgResolutionTime = totalTime / resolvedComplaints.length / (1000 * 60 * 60); // Convert to hours
      }
      
      return stats;
    } catch (error) {
      logger.error('Failed to get complaint stats', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  async transaction<T>(
    updateFunction: (transaction: FirebaseFirestore.Transaction) => Promise<T>
  ): Promise<T> {
    try {
      return await this.db.runTransaction(updateFunction);
    } catch (error) {
      logger.error('Transaction failed', error as Error);
      throw error;
    }
  }

  async exists(collection: string, docId: string): Promise<boolean> {
    try {
      const docRef = this.db.collection(collection).doc(docId);
      const docSnap = await docRef.get();
      return docSnap.exists;
    } catch (error) {
      logger.error(`Failed to check document existence ${collection}/${docId}`, error as Error);
      return false;
    }
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  async healthCheck(): Promise<boolean> {
    try {
      await this.db.collection('health').doc('check').get();
      return true;
    } catch (error) {
      logger.error('Firestore health check failed', error as Error);
      return false;
    }
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const firestoreAdmin = new FirestoreAdminClient();
