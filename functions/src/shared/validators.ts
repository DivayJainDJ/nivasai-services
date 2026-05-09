/**
 * Zod validation schemas for NivasAI Services
 */

import { z } from 'zod';

// ============================================================================
// Common Validators
// ============================================================================

const coordinateSchema = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

const addressSchema = z.object({
  line1: z.string().min(1, 'Address line 1 is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().min(1, 'State is required'),
  pincode: z.string().regex(/^\d{6}$/, 'Invalid PIN code format'),
});

// ============================================================================
// Complaint Validation
// ============================================================================

export const complaintSchema = z.object({
  id: z.string(),
  userId: z.string().min(1, 'User ID is required'),
  title: z.string().min(3, 'Title must be at least 3 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  category: z.enum(['water', 'sanitation', 'roads', 'electricity', 'waste', 'eviction', 'housing', 'other']).optional(),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  status: z.enum(['pending', 'in_progress', 'resolved', 'escalated', 'classification-failed']),
  location: z.object({
    lat: z.number().min(-90).max(90),
    lng: z.number().min(-180).max(180),
    address: z.string().min(1, 'Address is required'),
  }),
  wardId: z.string().min(1, 'Ward ID is required'),
  photoUrl: z.string().url().optional(),
  geminiSummary: z.string().optional(),
  suggestedDepartment: z.string().optional(),
  routedTo: z.string().optional(),
  routedAt: z.date().optional(),
  notificationSent: z.boolean().optional(),
  classifiedAt: z.date().optional(),
  createdAt: z.date(),
  updatedAt: z.date().optional(),
});

export const geminiClassificationSchema = z.object({
  category: z.string().min(1, 'Category is required'),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  summary: z.string().min(1, 'Summary is required'),
  suggestedDepartment: z.string().min(1, 'Suggested department is required'),
  confidence: z.number().min(0).max(1),
});

// ============================================================================
// Housing Validation
// ============================================================================

export const familyProfileSchema = z.object({
  id: z.string(),
  userId: z.string().min(1, 'User ID is required'),
  headOfFamily: z.object({
    name: z.string().min(2, 'Head of family name is required'),
    phone: z.string().regex(/^\+91\d{10}$/, 'Invalid Indian phone number'),
    aadhaar: z.string().regex(/^\d{12}$/, 'Invalid Aadhaar number').optional(),
  }),
  householdSize: z.number().min(1).max(20, 'Household size must be between 1 and 20'),
  monthlyIncome: z.number().min(0, 'Monthly income cannot be negative'),
  category: z.enum(['ews', 'lig', 'mig', 'hig']),
  currentAddress: addressSchema.extend({
    coordinates: coordinateSchema.optional(),
  }),
  currentHousing: z.object({
    type: z.enum(['kutcha', 'pucca', 'semi-pucca']),
    ownership: z.enum(['owned', 'rented', 'shared']),
    areaSqft: z.number().min(100, 'Area must be at least 100 sq ft'),
    rooms: z.number().min(1).max(10, 'Rooms must be between 1 and 10'),
    condition: z.enum(['poor', 'average', 'good']),
  }),
  documents: z.array(z.object({
    id: z.string(),
    type: z.enum(['aadhaar', 'pan', 'income_certificate', 'rent_agreement', 'ration_card']),
    url: z.string().url(),
    status: z.enum(['pending', 'verified', 'rejected', 'needs_review']),
    extractedData: z.record(z.unknown()).optional(),
    verifiedAt: z.date().optional(),
    uploadedAt: z.date(),
  })),
  preferences: z.object({
    minRooms: z.number().min(1).max(5, 'Minimum rooms must be between 1 and 5'),
    preferredAreas: z.array(z.string()),
    accessibility: z.boolean(),
  }),
  eligibility: z.object({
    ews: z.boolean(),
    lig: z.boolean(),
    mig: z.boolean(),
    hig: z.boolean(),
    pmay: z.boolean(),
    reason: z.string(),
  }),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export const housingUnitSchema = z.object({
  id: z.string(),
  scheme: z.enum(['pmay', 'rajasthan', 'karnataka', 'private']),
  address: addressSchema.extend({
    area: z.string().min(1, 'Area is required'),
    coordinates: coordinateSchema,
  }),
  specifications: z.object({
    areaSqft: z.number().min(100, 'Area must be at least 100 sq ft'),
    bedrooms: z.number().min(0).max(5, 'Bedrooms must be between 0 and 5'),
    bathrooms: z.number().min(0).max(3, 'Bathrooms must be between 0 and 3'),
    floor: z.number().min(0, 'Floor cannot be negative'),
    type: z.enum(['1bhk', '2bhk', '3bhk', 'studio']),
    parking: z.boolean(),
  }),
  financial: z.object({
    price: z.number().min(0, 'Price cannot be negative'),
    subsidy: z.number().min(0, 'Subsidy cannot be negative'),
    emi: z.number().min(0, 'EMI cannot be negative'),
    tenureMonths: z.number().min(1, 'Tenure must be at least 1 month'),
  }),
  eligibility: z.object({
    category: z.array(z.enum(['ews', 'lig', 'mig', 'hig'])),
    incomeMin: z.number().min(0),
    incomeMax: z.number().positive(),
    documents: z.array(z.string()),
  }),
  nearbyFacilities: z.object({
    schools: z.number().min(0),
    hospitals: z.number().min(0),
    transport: z.number().min(0),
    markets: z.number().min(0),
  }),
  status: z.enum(['available', 'booked', 'under_construction', 'maintenance']),
  possessionDate: z.date(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// ============================================================================
// Ward Validation
// ============================================================================

export const wardSchema = z.object({
  id: z.string(),
  name: z.string().min(1, 'Ward name is required'),
  number: z.string().min(1, 'Ward number is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().min(1, 'State is required'),
  coordinates: z.object({
    center: coordinateSchema,
    bounds: z.object({
      northeast: coordinateSchema,
      southwest: coordinateSchema,
    }),
  }),
  population: z.number().min(0, 'Population cannot be negative'),
  area: z.number().min(0, 'Area cannot be negative'),
  demographics: z.object({
    avgHouseholdSize: z.number().min(1),
    slumPopulation: z.number().min(0),
    literacyRate: z.number().min(0).max(100),
  }),
  infraScore: z.object({
    water: z.number().min(0).max(100),
    sanitation: z.number().min(0).max(100),
    roads: z.number().min(0).max(100),
    power: z.number().min(0).max(100),
    overall: z.number().min(0).max(100),
  }),
  lastUpdated: z.date(),
});

export const wardAnalysisSchema = z.object({
  wardId: z.string(),
  scores: z.object({
    roadConnectivity: z.number().min(0).max(10),
    waterAccess: z.number().min(0).max(10),
    sanitationCoverage: z.number().min(0).max(10),
    electricityAccess: z.number().min(0).max(10),
    greenCoverage: z.number().min(0).max(10),
    informalSettlements: z.number().min(0).max(10),
  }),
  summary: z.string().min(1, 'Summary is required'),
  topPriority: z.string().min(1, 'Top priority is required'),
  estimatedPopulation: z.number().min(0),
  analyzedAt: z.date(),
});

// ============================================================================
// API Request Validation
// ============================================================================

export const analyzeWardRequestSchema = z.object({
  wardId: z.string().min(1, 'Ward ID is required'),
  wardName: z.string().min(1, 'Ward name is required'),
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

export const matchHousingRequestSchema = z.object({
  familyProfile: familyProfileSchema.omit({ id: true, userId: true, createdAt: true, updatedAt: true }),
});

export const analyzeWardResponseSchema = z.object({
  analysis: wardAnalysisSchema,
  report: z.object({
    projects: z.array(z.object({
      name: z.string().min(1),
      cost: z.number().min(0),
      timeline: z.string().min(1),
      description: z.string().min(1),
      priority: z.enum(['high', 'medium', 'low']),
    })),
  }),
});

export const matchHousingResponseSchema = z.object({
  matches: z.array(z.object({
    unit: housingUnitSchema,
    score: z.number().min(0).max(100),
    explanation: z.string().min(1),
    eligibility: z.object({
      eligible: z.boolean(),
      missingDocuments: z.array(z.string()),
      incomeGap: z.number().min(0),
    }),
    distance: z.number().min(0),
  })),
});

// ============================================================================
// Bot Validation
// ============================================================================

export const botIntentSchema = z.object({
  intent: z.enum(['FILE_COMPLAINT', 'CHECK_STATUS', 'FIND_HOUSING', 'GREET', 'UNKNOWN']),
  entities: z.record(z.unknown()),
});

export const twilioWebhookSchema = z.object({
  From: z.string().min(1, 'From number is required'),
  To: z.string().min(1, 'To number is required'),
  Body: z.string(),
  MediaUrl0: z.string().url().optional(),
  MessageSid: z.string().min(1, 'Message SID is required'),
  AccountSid: z.string().min(1, 'Account SID is required'),
});

// ============================================================================
// Notification Validation
// ============================================================================

export const notificationPayloadSchema = z.object({
  wardId: z.string().optional(),
  type: z.enum(['complaint', 'housing', 'ward_analysis', 'system']),
  message: z.string().min(1, 'Message is required'),
  recipientRole: z.enum(['resident', 'officer', 'admin']).optional(),
  data: z.record(z.unknown()).optional(),
});

export const fcmTokenSchema = z.object({
  userId: z.string().min(1),
  token: z.string().min(1),
  role: z.string().min(1),
  deviceInfo: z.object({
    platform: z.string().min(1),
    version: z.string().min(1),
  }),
  createdAt: z.date(),
  lastUsed: z.date(),
});

// ============================================================================
// Analytics Validation
// ============================================================================

export const wardStatsSchema = z.object({
  wardId: z.string(),
  timestamp: z.date(),
  totalComplaints: z.number().min(0),
  unresolvedComplaints: z.number().min(0),
  pressureScore: z.number().min(0).max(1),
  avgResolutionTime: z.number().min(0),
  housingMatches: z.number().min(0),
  population: z.number().min(0),
  infraScore: z.number().min(0).max(100),
});

export const complaintEventSchema = z.object({
  complaintId: z.string(),
  wardId: z.string(),
  event: z.enum(['created', 'classified', 'routed', 'resolved', 'escalated']),
  timestamp: z.date(),
  data: z.record(z.unknown()).optional(),
});

// ============================================================================
// Document Validation
// ============================================================================

export const documentUploadSchema = z.object({
  id: z.string(),
  userId: z.string().min(1),
  type: z.enum(['aadhaar', 'pan', 'income_certificate', 'rent_agreement', 'ration_card']),
  url: z.string().url(),
  uploadedAt: z.date(),
});

// ============================================================================
// Utility Validators
// ============================================================================

export const phoneNumberSchema = z.string().regex(/^\+91\d{10}$/, 'Invalid Indian phone number format');

export const aadhaarSchema = z.string().regex(/^\d{12}$/, 'Invalid Aadhaar number format');

export const panSchema = z.string().regex(/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, 'Invalid PAN number format');

export const emailSchema = z.string().email('Invalid email address');

export const pincodeSchema = z.string().regex(/^\d{6}$/, 'Invalid PIN code format');

// ============================================================================
// Environment Variable Validation
// ============================================================================

export const envSchema = z.object({
  GEMINI_API_KEY: z.string().min(1, 'Gemini API key is required'),
  GOOGLE_MAPS_KEY: z.string().min(1, 'Google Maps API key is required'),
  TWILIO_ACCOUNT_SID: z.string().min(1, 'Twilio Account SID is required'),
  TWILIO_AUTH_TOKEN: z.string().min(1, 'Twilio Auth Token is required'),
  TWILIO_WHATSAPP_NUMBER: z.string().min(1, 'Twilio WhatsApp number is required'),
  DOCUMENT_AI_PROJECT_ID: z.string().min(1, 'Document AI Project ID is required'),
  DOCUMENT_AI_LOCATION: z.string().min(1, 'Document AI location is required'),
  DOCUMENT_AI_PROCESSOR_ID: z.string().min(1, 'Document AI Processor ID is required'),
  BIGQUERY_DATASET: z.string().min(1, 'BigQuery dataset is required'),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  MAX_RETRIES: z.string().transform(Number).pipe(z.number().min(1).max(10)).default('3'),
  RETRY_DELAY_MS: z.string().transform(Number).pipe(z.number().min(100)).default('1000'),
  FCM_MAX_BATCH_SIZE: z.string().transform(Number).pipe(z.number().min(1).max(1000)).default('500'),
});

// ============================================================================
// Export Types
// ============================================================================

export type IComplaint = z.infer<typeof complaintSchema>;
export type IGeminiClassification = z.infer<typeof geminiClassificationSchema>;
export type IFamilyProfile = z.infer<typeof familyProfileSchema>;
export type IHousingUnit = z.infer<typeof housingUnitSchema>;
export type IWard = z.infer<typeof wardSchema>;
export type IWardAnalysis = z.infer<typeof wardAnalysisSchema>;
export type IAnalyzeWardRequest = z.infer<typeof analyzeWardRequestSchema>;
export type IAnalyzeWardResponse = z.infer<typeof analyzeWardResponseSchema>;
export type IMatchHousingRequest = z.infer<typeof matchHousingRequestSchema>;
export type IMatchHousingResponse = z.infer<typeof matchHousingResponseSchema>;
export type IBotIntent = z.infer<typeof botIntentSchema>;
export type ITwilioWebhook = z.infer<typeof twilioWebhookSchema>;
export type INotificationPayload = z.infer<typeof notificationPayloadSchema>;
export type IFCMToken = z.infer<typeof fcmTokenSchema>;
export type IWardStats = z.infer<typeof wardStatsSchema>;
export type IComplaintEvent = z.infer<typeof complaintEventSchema>;
export type IDocumentUpload = z.infer<typeof documentUploadSchema>;
export type IEnv = z.infer<typeof envSchema>;
