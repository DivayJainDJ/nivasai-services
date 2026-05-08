/**
 * Shared TypeScript interfaces for NivasAI Services
 */

// ============================================================================
// Core Data Types
// ============================================================================

export interface IComplaint {
  readonly id: string
  readonly userId: string
  readonly title: string
  readonly description: string
  readonly category?: string
  readonly severity?: 'low' | 'medium' | 'high' | 'critical'
  readonly status: 'pending' | 'in_progress' | 'resolved' | 'escalated' | 'classification-failed'
  readonly location: {
    readonly lat: number
    readonly lng: number
    readonly address: string
  }
  readonly wardId: string
  readonly photoUrl?: string
  readonly geminiSummary?: string
  readonly suggestedDepartment?: string
  readonly routedTo?: string
  readonly routedAt?: Date
  readonly notificationSent?: boolean
  readonly classifiedAt?: Date
  readonly createdAt: Date
  readonly updatedAt?: Date
}

export interface IFamilyProfile {
  readonly id: string
  readonly userId: string
  readonly headOfFamily: {
    readonly name: string
    readonly phone: string
    readonly aadhaar?: string
  }
  readonly householdSize: number
  readonly monthlyIncome: number
  readonly category: 'ews' | 'lig' | 'mig' | 'hig'
  readonly currentAddress: {
    readonly line1: string
    readonly city: string
    readonly state: string
    readonly pincode: string
    readonly coordinates?: {
      readonly lat: number
      readonly lng: number
    }
  }
  readonly currentHousing: {
    readonly type: 'kutcha' | 'pucca' | 'semi-pucca'
    readonly ownership: 'owned' | 'rented' | 'shared'
    readonly areaSqft: number
    readonly rooms: number
    readonly condition: 'poor' | 'average' | 'good'
  }
  readonly documents: readonly IHousingDocument[]
  readonly preferences: {
    readonly minRooms: number
    readonly preferredAreas: readonly string[]
    readonly accessibility: boolean
  }
  readonly eligibility: {
    readonly ews: boolean
    readonly lig: boolean
    readonly mig: boolean
    readonly hig: boolean
    readonly pmay: boolean
    readonly reason: string
  }
  readonly createdAt: Date
  readonly updatedAt: Date
}

export interface IHousingUnit {
  readonly id: string
  readonly scheme: 'pmay' | 'rajasthan' | 'karnataka' | 'private'
  readonly address: {
    readonly line1: string
    readonly area: string
    readonly city: string
    readonly state: string
    readonly pincode: string
    readonly coordinates: {
      readonly lat: number
      readonly lng: number
    }
  }
  readonly specifications: {
    readonly areaSqft: number
    readonly bedrooms: number
    readonly bathrooms: number
    readonly floor: number
    readonly type: '1bhk' | '2bhk' | '3bhk' | 'studio'
    readonly parking: boolean
  }
  readonly financial: {
    readonly price: number
    readonly subsidy: number
    readonly emi: number
    readonly tenureMonths: number
  }
  readonly eligibility: {
    readonly category: readonly ('ews' | 'lig' | 'mig' | 'hig')[]
    readonly incomeMin: number
    readonly incomeMax: number
    readonly documents: readonly string[]
  }
  readonly nearbyFacilities: {
    readonly schools: number
    readonly hospitals: number
    readonly transport: number
    readonly markets: number
  }
  readonly status: 'available' | 'booked' | 'under_construction' | 'maintenance'
  readonly possessionDate: Date
  readonly createdAt: Date
  readonly updatedAt: Date
}

export interface IHousingDocument {
  readonly id: string
  readonly type: 'aadhaar' | 'pan' | 'income_certificate' | 'rent_agreement' | 'ration_card'
  readonly url: string
  readonly status: 'pending' | 'verified' | 'rejected' | 'needs_review'
  readonly extractedData?: Record<string, unknown>
  readonly verifiedAt?: Date
  readonly uploadedAt: Date
}

export interface IWard {
  readonly id: string
  readonly name: string
  readonly number: string
  readonly city: string
  readonly state: string
  readonly coordinates: {
    readonly center: { readonly lat: number; readonly lng: number }
    readonly bounds: {
      readonly northeast: { readonly lat: number; readonly lng: number }
      readonly southwest: { readonly lat: number; readonly lng: number }
    }
  }
  readonly population: number
  readonly area: number
  readonly demographics: {
    readonly avgHouseholdSize: number
    readonly slumPopulation: number
    readonly literacyRate: number
  }
  readonly infraScore: {
    readonly water: number
    readonly sanitation: number
    readonly roads: number
    readonly power: number
    readonly overall: number
  }
  readonly lastUpdated: Date
}

// ============================================================================
// AI/Analysis Types
// ============================================================================

export interface IGeminiClassification {
  readonly category: string
  readonly severity: 'low' | 'medium' | 'high' | 'critical'
  readonly summary: string
  readonly suggestedDepartment: string
  readonly confidence: number
}

export interface IWardAnalysis {
  readonly wardId: string
  readonly scores: {
    readonly roadConnectivity: number
    readonly waterAccess: number
    readonly sanitationCoverage: number
    readonly electricityAccess: number
    readonly greenCoverage: number
    readonly informalSettlements: number
  }
  readonly summary: string
  readonly topPriority: string
  readonly estimatedPopulation: number
  readonly analyzedAt: Date
}

export interface IUpgradeProject {
  readonly name: string
  readonly cost: number
  readonly timeline: string
  readonly description: string
  readonly priority: 'high' | 'medium' | 'low'
}

export interface IHousingMatch {
  readonly unit: IHousingUnit
  readonly score: number
  readonly explanation: string
  readonly eligibility: {
    readonly eligible: boolean
    readonly missingDocuments: readonly string[]
    readonly incomeGap: number
  }
  readonly distance: number
}

// ============================================================================
// Notification Types
// ============================================================================

export interface INotificationPayload {
  readonly wardId?: string
  readonly type: 'complaint' | 'housing' | 'ward_analysis' | 'system'
  readonly message: string
  readonly recipientRole?: 'resident' | 'officer' | 'admin'
  readonly data?: Record<string, unknown>
}

export interface IFCMToken {
  readonly userId: string
  readonly token: string
  readonly role: string
  readonly deviceInfo: {
    readonly platform: string
    readonly version: string
  }
  readonly createdAt: Date
  readonly lastUsed: Date
}

// ============================================================================
// Bot/Chat Types
// ============================================================================

export interface IBotIntent {
  readonly intent: 'FILE_COMPLAINT' | 'CHECK_STATUS' | 'FIND_HOUSING' | 'GREET' | 'UNKNOWN'
  readonly entities: Record<string, unknown>
}

export interface IBotSession {
  readonly sessionId: string
  readonly phoneNumber: string
  readonly currentIntent?: string
  readonly context: Record<string, unknown>
  readonly messages: readonly IBotMessage[]
  readonly createdAt: Date
  readonly updatedAt: Date
}

export interface IBotMessage {
  readonly id: string
  readonly type: 'user' | 'bot'
  readonly content: string
  readonly mediaUrl?: string
  readonly timestamp: Date
}

// ============================================================================
// Analytics Types
// ============================================================================

export interface IComplaintEvent {
  readonly complaintId: string
  readonly wardId: string
  readonly event: 'created' | 'classified' | 'routed' | 'resolved' | 'escalated'
  readonly timestamp: Date
  readonly data?: Record<string, unknown>
}

export interface IWardStats {
  readonly wardId: string
  readonly timestamp: Date
  readonly totalComplaints: number
  readonly unresolvedComplaints: number
  readonly pressureScore: number
  readonly avgResolutionTime: number
  readonly housingMatches: number
  readonly population: number
  readonly infraScore: number
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface IAnalyzeWardRequest {
  readonly wardId: string
  readonly wardName: string
  readonly lat: number
  readonly lng: number
}

export interface IAnalyzeWardResponse {
  readonly analysis: IWardAnalysis
  readonly report: {
    readonly projects: readonly IUpgradeProject[]
  }
}

export interface IMatchHousingRequest {
  readonly familyProfile: IFamilyProfile
}

export interface IMatchHousingResponse {
  readonly matches: readonly IHousingMatch[]
}

export interface IDocumentUpload {
  readonly id: string
  readonly userId: string
  readonly type: string
  readonly url: string
  readonly uploadedAt: Date
}

// ============================================================================
// Error Types
// ============================================================================

export interface IServiceError extends Error {
  readonly code: string
  readonly details?: Record<string, unknown>
  readonly retryable: boolean
}

// ============================================================================
// Configuration Types
// ============================================================================

export interface IServiceConfig {
  readonly maxRetries: number
  readonly retryDelayMs: number
  readonly timeoutMs: number
  readonly batchSize: number
}

// ============================================================================
// Pub/Sub Message Types
// ============================================================================

export interface IPubSubMessage<T = unknown> {
  readonly data: T
  readonly attributes?: Record<string, string>
  readonly messageId: string
  readonly publishTime: string
}

export interface IComplaintClassifiedMessage extends IPubSubMessage<{
  readonly complaintId: string
  readonly classification: IGeminiClassification
}> {}

export interface IBroadcastNotificationMessage extends IPubSubMessage<INotificationPayload> {}

// ============================================================================
// Twilio Types
// ============================================================================

export interface ITwilioWebhook {
  readonly From: string
  readonly To: string
  readonly Body: string
  readonly MediaUrl0?: string
  readonly MessageSid: string
  readonly AccountSid: string
}

export interface ITwilioResponse {
  readonly to: string
  readonly from: string
  readonly body: string
  readonly mediaUrl?: string[]
}
