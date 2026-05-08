/**
 * BigQuery Client wrapper for analytics and logging
 */

import { BigQuery } from '@google-cloud/bigquery';
import { withBigQueryRetry } from './retryHelper';
import { logger } from './logger';
import { IComplaintEvent, IWardStats } from './types';

// ============================================================================
// BigQuery Client Class
// ============================================================================

export class BigQueryClient {
  private readonly bigquery: BigQuery;
  private readonly datasetId: string;

  constructor() {
    this.datasetId = process.env.BIGQUERY_DATASET || 'nivasai_analytics';
    this.bigquery = new BigQuery({
      projectId: process.env.DOCUMENT_AI_PROJECT_ID || process.env.FIREBASE_PROJECT_ID,
    });
  }

  // ============================================================================
  // Table Operations
  // ============================================================================

  async ensureTableExists(tableId: string, schema: any[]): Promise<void> {
    try {
      const dataset = this.bigquery.dataset(this.datasetId);
      const table = dataset.table(tableId);
      const [exists] = await table.exists();

      if (!exists) {
        await this.createTable(tableId, schema);
      }
    } catch (error) {
      logger.error(`Failed to ensure table exists: ${tableId}`, error as Error);
      throw error;
    }
  }

  private async createTable(tableId: string, schema: any[]): Promise<void> {
    try {
      const dataset = this.bigquery.dataset(this.datasetId);
      const [table] = await dataset.createTable(tableId, { schema });

      logger.info(`Created BigQuery table: ${tableId}`, {
        tableId: table.id,
        schemaFields: schema.length,
      });
    } catch (error) {
      logger.error(`Failed to create table: ${tableId}`, error as Error);
      throw error;
    }
  }

  // ============================================================================
  // Data Insertion
  // ============================================================================

  async insertComplaintEvent(event: IComplaintEvent): Promise<void> {
    return withBigQueryRetry(async () => {
      try {
        const tableId = 'complaint_events';
        const schema = [
          { name: 'complaintId', type: 'STRING' },
          { name: 'wardId', type: 'STRING' },
          { name: 'event', type: 'STRING' },
          { name: 'timestamp', type: 'TIMESTAMP' },
          { name: 'data', type: 'JSON' },
        ];

        await this.ensureTableExists(tableId, schema);

        const table = this.bigquery.dataset(this.datasetId).table(tableId);
        
        await table.insert({
          complaintId: event.complaintId,
          wardId: event.wardId,
          event: event.event,
          timestamp: event.timestamp,
          data: JSON.stringify(event.data || {}),
        });

        logger.debug('Complaint event inserted into BigQuery', {
          complaintId: event.complaintId,
          event: event.event,
        });
      } catch (error) {
        logger.error('Failed to insert complaint event', error as Error, {
          complaintId: event.complaintId,
        });
        throw error;
      }
    }, 'insertComplaintEvent');
  }

  async insertWardStats(stats: IWardStats): Promise<void> {
    return withBigQueryRetry(async () => {
      try {
        const tableId = 'ward_stats';
        const schema = [
          { name: 'wardId', type: 'STRING' },
          { name: 'timestamp', type: 'TIMESTAMP' },
          { name: 'totalComplaints', type: 'INTEGER' },
          { name: 'unresolvedComplaints', type: 'INTEGER' },
          { name: 'pressureScore', type: 'FLOAT' },
          { name: 'avgResolutionTime', type: 'FLOAT' },
          { name: 'housingMatches', type: 'INTEGER' },
          { name: 'population', type: 'INTEGER' },
          { name: 'infraScore', type: 'INTEGER' },
        ];

        await this.ensureTableExists(tableId, schema);

        const table = this.bigquery.dataset(this.datasetId).table(tableId);
        
        await table.insert({
          wardId: stats.wardId,
          timestamp: stats.timestamp,
          totalComplaints: stats.totalComplaints,
          unresolvedComplaints: stats.unresolvedComplaints,
          pressureScore: stats.pressureScore,
          avgResolutionTime: stats.avgResolutionTime,
          housingMatches: stats.housingMatches,
          population: stats.population,
          infraScore: stats.infraScore,
        });

        logger.debug('Ward stats inserted into BigQuery', {
          wardId: stats.wardId,
          pressureScore: stats.pressureScore,
        });
      } catch (error) {
        logger.error('Failed to insert ward stats', error as Error, {
          wardId: stats.wardId,
        });
        throw error;
      }
    }, 'insertWardStats');
  }

  async insertBatchEvents(events: IComplaintEvent[]): Promise<void> {
    return withBigQueryRetry(async () => {
      try {
        if (events.length === 0) return;

        const tableId = 'complaint_events';
        const schema = [
          { name: 'complaintId', type: 'STRING' },
          { name: 'wardId', type: 'STRING' },
          { name: 'event', type: 'STRING' },
          { name: 'timestamp', type: 'TIMESTAMP' },
          { name: 'data', type: 'JSON' },
        ];

        await this.ensureTableExists(tableId, schema);

        const table = this.bigquery.dataset(this.datasetId).table(tableId);
        
        const rows = events.map(event => ({
          complaintId: event.complaintId,
          wardId: event.wardId,
          event: event.event,
          timestamp: event.timestamp,
          data: JSON.stringify(event.data || {}),
        }));

        await table.insert(rows);

        logger.info('Batch complaint events inserted into BigQuery', {
          eventCount: events.length,
        });
      } catch (error) {
        logger.error('Failed to insert batch complaint events', error as Error, {
          eventCount: events.length,
        });
        throw error;
      }
    }, 'insertBatchEvents');
  }

  // ============================================================================
  // Query Operations
  // ============================================================================

  async getComplaintTrends(
    wardId?: string,
    days: number = 30
  ): Promise<Array<{
    date: string;
    total: number;
    byCategory: Record<string, number>;
    byStatus: Record<string, number>;
  }>> {
    try {
      let query = `
        SELECT
          DATE(timestamp) as date,
          COUNT(*) as total,
          JSON_OBJECT_AGG(CASE WHEN data.category IS NOT NULL THEN JSON_EXTRACT_SCALAR(data, '$.category') ELSE 'other' END) as byCategory,
          JSON_OBJECT_AGG(event) as byStatus
        FROM \`${this.datasetId}.complaint_events\`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ${days} DAY)
      `;

      const params: any[] = [];

      if (wardId) {
        query += ` AND wardId = ?`;
        params.push(wardId);
      }

      query += `
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
      `;

      const [rows] = await this.bigquery.query({
        query,
        params,
      });

      return rows.map((row: any) => ({
        date: row.date.value,
        total: parseInt(row.total.value),
        byCategory: JSON.parse(row.byCategory.value || '{}'),
        byStatus: JSON.parse(row.byStatus.value || '{}'),
      }));
    } catch (error) {
      logger.error('Failed to get complaint trends', error as Error, { wardId, days });
      throw error;
    }
  }

  async getWardPerformanceMetrics(
    wardId?: string,
    days: number = 7
  ): Promise<Array<{
    wardId: string;
    avgResolutionTime: number;
    complaintVolume: number;
    pressureScore: number;
    trend: 'improving' | 'declining' | 'stable';
  }>> {
    try {
      let query = `
        SELECT
          wardId,
          AVG(CASE 
            WHEN event = 'resolved' AND data.resolutionTime IS NOT NULL 
            THEN JSON_EXTRACT_SCALAR(data, '$.resolutionTime') 
            ELSE NULL 
          END) as avgResolutionTime,
          COUNT(*) as complaintVolume,
          AVG(
            CASE 
              WHEN event = 'created' 
              THEN 1 
              WHEN event = 'resolved' 
              THEN -1 
              ELSE 0 
            END
          ) as pressureScore
        FROM \`${this.datasetId}.complaint_events\`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ${days} DAY)
      `;

      const params: any[] = [];

      if (wardId) {
        query += ` AND wardId = ?`;
        params.push(wardId);
      }

      query += `
        GROUP BY wardId
        ORDER BY pressureScore DESC
      `;

      const [rows] = await this.bigquery.query({
        query,
        params,
      });

      return rows.map((row: any) => ({
        wardId: row.wardId.value,
        avgResolutionTime: parseFloat(row.avgResolutionTime.value) || 0,
        complaintVolume: parseInt(row.complaintVolume.value),
        pressureScore: parseFloat(row.pressureScore.value) || 0,
        trend: 'stable', // Would need more complex logic to calculate trend
      }));
    } catch (error) {
      logger.error('Failed to get ward performance metrics', error as Error, { wardId, days });
      throw error;
    }
  }

  async getTopWardsByPressure(limit: number = 10): Promise<Array<{
    wardId: string;
    pressureScore: number;
    totalComplaints: number;
    unresolvedComplaints: number;
  }>> {
    try {
      const query = `
        SELECT
          wardId,
          AVG(pressureScore) as pressureScore,
          COUNT(*) as totalComplaints,
          SUM(CASE WHEN status = 'unresolved' THEN 1 ELSE 0 END) as unresolvedComplaints
        FROM \`${this.datasetId}.ward_stats\`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY wardId
        ORDER BY pressureScore DESC
        LIMIT ?
      `;

      const [rows] = await this.bigquery.query({
        query,
        params: [limit],
      });

      return rows.map((row: any) => ({
        wardId: row.wardId.value,
        pressureScore: parseFloat(row.pressureScore.value),
        totalComplaints: parseInt(row.totalComplaints.value),
        unresolvedComplaints: parseInt(row.unresolvedComplaints.value),
      }));
    } catch (error) {
      logger.error('Failed to get top wards by pressure', error as Error, { limit });
      throw error;
    }
  }

  // ============================================================================
  // Analytics Helper Methods
  ============================================================================

  async calculatePressureScore(wardId: string, days: number = 30): Promise<number> {
    try {
      const query = `
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN event = 'resolved' THEN 1 ELSE 0 END) as resolved
        FROM \`${this.datasetId}.complaint_events\`
        WHERE wardId = ? 
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ${days} DAY)
          AND event IN ('created', 'resolved')
      `;

      const [rows] = await this.bigquery.query({
        query,
        params: [wardId],
      });

      if (rows.length === 0) return 0;

      const row = rows[0];
      const total = parseInt(row.total.value);
      const resolved = parseInt(row.resolved.value);
      
      return total > 0 ? (total - resolved) / total : 0;
    } catch (error) {
      logger.error('Failed to calculate pressure score', error as Error, { wardId, days });
      return 0;
    }
  }

  async getHousingAnalytics(days: number = 30): Promise<{
    totalMatches: number;
    matchesByCategory: Record<string, number>;
    avgMatchScore: number;
    conversionRate: number;
  }> {
    try {
      // This would require additional housing analytics tables
      // For now, return placeholder data
      return {
        totalMatches: 0,
        matchesByCategory: {},
        avgMatchScore: 0,
        conversionRate: 0,
      };
    } catch (error) {
      logger.error('Failed to get housing analytics', error as Error, { days });
      throw error;
    }
  }

  // ============================================================================
  // Health Check
  ============================================================================

  async healthCheck(): Promise<boolean> {
    try {
      // Try to query the dataset to verify connectivity
      const [datasets] = await this.bigquery.getDatasets();
      const datasetExists = datasets.some(dataset => dataset.id === this.datasetId);
      
      return datasetExists;
    } catch (error) {
      logger.error('BigQuery health check failed', error as Error);
      return false;
    }
  }

  // ============================================================================
  // Utility Methods
  ============================================================================

  getDatasetId(): string {
    return this.datasetId;
  }

  async getTableInfo(tableId: string): Promise<{
    tableId: string;
    numRows: number;
    numBytes: number;
    created: Date;
    modified: Date;
  }> {
    try {
      const table = this.bigquery.dataset(this.datasetId).table(tableId);
      const [metadata] = await table.getMetadata();

      return {
        tableId: metadata.id.tableId,
        numRows: parseInt(metadata.numRows || '0'),
        numBytes: parseInt(metadata.numBytes || '0'),
        created: metadata.created ? new Date(metadata.created) : new Date(),
        modified: metadata.modified ? new Date(metadata.modified) : new Date(),
      };
    } catch (error) {
      logger.error('Failed to get table info', error as Error, { tableId });
      throw error;
    }
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const bigqueryClient = new BigQueryClient();
