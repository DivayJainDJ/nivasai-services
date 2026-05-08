/**
 * Gemini AI Client with retry wrapper and streaming support
 */

import { GoogleGenerativeAI, GenerativeModel } from '@google/generative-ai';
import { withGeminiRetry } from './retryHelper';
import { logger } from './logger';
import { IGeminiClassification } from './types';

// ============================================================================
// Configuration
// ============================================================================

interface IGeminiConfig {
  readonly apiKey: string;
  readonly model: string;
  readonly temperature: number;
  readonly topK: number;
  readonly topP: number;
  readonly maxOutputTokens: number;
}

const DEFAULT_CONFIG: IGeminiConfig = {
  apiKey: process.env.GEMINI_API_KEY || '',
  model: 'gemini-1.5-pro',
  temperature: 0.4,
  topK: 32,
  topP: 0.95,
  maxOutputTokens: 4096,
};

// ============================================================================
// Gemini Client Class
// ============================================================================

export class GeminiClient {
  private readonly config: IGeminiConfig;
  private readonly client: GoogleGenerativeAI;
  private readonly model: GenerativeModel;

  constructor(config: Partial<IGeminiConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };

    if (!this.config.apiKey) {
      throw new Error('Gemini API key is required');
    }

    this.client = new GoogleGenerativeAI(this.config.apiKey);
    this.model = this.client.getGenerativeModel({
      model: this.config.model,
      generationConfig: {
        temperature: this.config.temperature,
        topK: this.config.topK,
        topP: this.config.topP,
        maxOutputTokens: this.config.maxOutputTokens,
      },
      safetySettings: [
        {
          category: 'HARM_CATEGORY_HARASSMENT',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE',
        },
        {
          category: 'HARM_CATEGORY_HATE_SPEECH',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE',
        },
        {
          category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE',
        },
        {
          category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
          threshold: 'BLOCK_MEDIUM_AND_ABOVE',
        },
      ],
    });
  }

  // ============================================================================
  // Vision Analysis
  // ============================================================================

  async analyzeImage(
    imageData: string,
    prompt: string,
    context?: string
  ): Promise<{ text: string; confidence: number }> {
    const fullPrompt = context ? `${context}\n\n${prompt}` : prompt;

    return withGeminiRetry(async () => {
      logger.debug('Starting Gemini image analysis', {
        promptLength: fullPrompt.length,
        hasImageData: !!imageData,
      });

      const imagePart = {
        inlineData: {
          data: imageData,
          mimeType: 'image/jpeg',
        },
      };

      const textPart = {
        text: fullPrompt,
      };

      const result = await this.model.generateContent([imagePart, textPart]);
      const response = await result.response;
      const text = response.text();

      // Calculate confidence based on response characteristics
      const confidence = this.calculateConfidence(response);

      logger.info('Gemini image analysis completed', {
        responseLength: text.length,
        confidence,
      });

      return { text, confidence };
    }, 'analyzeImage');
  }

  async classifyComplaintImage(
    imageData: string,
    description: string
  ): Promise<IGeminiClassification> {
    const prompt = `
      Analyze this image of an urban infrastructure complaint from India. 
      Description: "${description}"
      
      Return JSON with these exact fields:
      {
        "category": "water|sanitation|roads|electricity|waste|eviction|housing|other",
        "severity": "low|medium|high|critical",
        "summary": "brief summary of the issue",
        "suggestedDepartment": "water|sanitation|roads|electricity|municipal|housing",
        "confidence": "number between 0 and 1"
      }
      
      Be specific and accurate. Focus on infrastructure issues common in Indian urban areas.
    `;

    const response = await this.analyzeImage(imageData, prompt, 'complaint-classification');

    try {
      const parsed = JSON.parse(response.text);
      
      // Validate and normalize the response
      const classification: IGeminiClassification = {
        category: parsed.category || 'other',
        severity: parsed.severity || 'medium',
        summary: parsed.summary || 'Infrastructure issue detected',
        suggestedDepartment: parsed.suggestedDepartment || 'municipal',
        confidence: typeof parsed.confidence === 'number' ? parsed.confidence : response.confidence,
      };

      logger.info('Complaint classification completed', {
        category: classification.category,
        severity: classification.severity,
        confidence: classification.confidence,
      });

      return classification;
    } catch (error) {
      logger.error('Failed to parse Gemini classification response', error as Error, {
        responseText: response.text,
      });

      // Return fallback classification
      return {
        category: 'other',
        severity: 'medium',
        summary: 'Unable to classify automatically',
        suggestedDepartment: 'municipal',
        confidence: 0.3,
      };
    }
  }

  async analyzeWardSatelliteImage(
    imageData: string,
    wardName: string
  ): Promise<{
    scores: {
      roadConnectivity: number;
      waterAccess: number;
      sanitationCoverage: number;
      electricityAccess: number;
      greenCoverage: number;
      informalSettlements: number;
    };
    summary: string;
    topPriority: string;
    estimatedPopulation: number;
  }> {
    const prompt = `
      You are analyzing a satellite image of an urban ward in India for infrastructure assessment.
      Ward Name: ${wardName}
      
      Identify and score each infrastructure aspect on a scale of 0-10:
      - roadConnectivity (paved roads visible, width, density)
      - waterAccess (pipelines, water bodies, tanker spots)
      - sanitationCoverage (drainage channels, open drains visible)
      - electricityAccess (power lines, transformer boxes)
      - greenCoverage (trees, parks)
      - informalSettlements (density of informal structures, estimated count)
      
      Also provide:
      - summary: brief analysis of overall infrastructure status
      - topPriority: most critical infrastructure need
      - estimatedPopulation: rough estimate based on visible structures
      
      Return JSON with these exact fields:
      {
        "scores": {
          "roadConnectivity": number,
          "waterAccess": number,
          "sanitationCoverage": number,
          "electricityAccess": number,
          "greenCoverage": number,
          "informalSettlements": number
        },
        "summary": "string",
        "topPriority": "string",
        "estimatedPopulation": number
      }
    `;

    const response = await this.analyzeImage(imageData, prompt, 'ward-analysis');

    try {
      const parsed = JSON.parse(response.text);
      
      // Validate scores are within 0-10 range
      const scores = {
        roadConnectivity: Math.max(0, Math.min(10, parsed.scores?.roadConnectivity || 5)),
        waterAccess: Math.max(0, Math.min(10, parsed.scores?.waterAccess || 5)),
        sanitationCoverage: Math.max(0, Math.min(10, parsed.scores?.sanitationCoverage || 5)),
        electricityAccess: Math.max(0, Math.min(10, parsed.scores?.electricityAccess || 5)),
        greenCoverage: Math.max(0, Math.min(10, parsed.scores?.greenCoverage || 5)),
        informalSettlements: Math.max(0, Math.min(10, parsed.scores?.informalSettlements || 5)),
      };

      return {
        scores,
        summary: parsed.summary || 'Infrastructure analysis completed',
        topPriority: parsed.topPriority || 'General infrastructure improvement',
        estimatedPopulation: Math.max(0, parsed.estimatedPopulation || 1000),
      };
    } catch (error) {
      logger.error('Failed to parse ward analysis response', error as Error, {
        responseText: response.text,
      });

      // Return fallback analysis
      return {
        scores: {
          roadConnectivity: 5,
          waterAccess: 5,
          sanitationCoverage: 5,
          electricityAccess: 5,
          greenCoverage: 5,
          informalSettlements: 5,
        },
        summary: 'Unable to complete detailed analysis',
        topPriority: 'Needs manual assessment',
        estimatedPopulation: 1000,
      };
    }
  }

  // ============================================================================
  // Text Generation
  // ============================================================================

  async generateText(
    prompt: string,
    context?: string,
    options?: {
      temperature?: number;
      maxTokens?: number;
    }
  ): Promise<string> {
    const fullPrompt = context ? `${context}\n\n${prompt}` : prompt;

    return withGeminiRetry(async () => {
      logger.debug('Starting Gemini text generation', {
        promptLength: fullPrompt.length,
        temperature: options?.temperature,
        maxTokens: options?.maxTokens,
      });

      const modelConfig = options ? {
        temperature: options.temperature,
        maxOutputTokens: options.maxTokens,
      } : {};

      const model = this.client.getGenerativeModel({
        model: this.config.model,
        generationConfig: {
          ...this.model.generationConfig,
          ...modelConfig,
        },
      });

      const result = await model.generateContent(fullPrompt);
      const response = await result.response;
      const text = response.text();

      logger.info('Gemini text generation completed', {
        responseLength: text.length,
      });

      return text;
    }, 'generateText');
  }

  async generateUpgradeReport(
    wardName: string,
    scores: Record<string, number>,
    population: number
  ): Promise<{
    projects: Array<{
      name: string;
      cost: number;
      timeline: string;
      description: string;
      priority: 'high' | 'medium' | 'low';
    }>;
  }> {
    const prompt = `
      Given these infrastructure scores for ${wardName} (population: ${population}):
      ${JSON.stringify(scores, null, 2)}
      
      Generate a detailed remediation plan with specific projects.
      For each project, provide:
      - name: clear project title
      - cost: estimated cost in INR (be realistic for Indian context)
      - timeline: implementation duration
      - description: what the project involves
      - priority: high/medium/low based on urgency
      
      Focus on infrastructure improvements that will have maximum impact.
      Consider typical costs for Indian urban infrastructure projects.
      
      Return JSON with this exact structure:
      {
        "projects": [
          {
            "name": "string",
            "cost": number,
            "timeline": "string (e.g., '6 months', '1 year')",
            "description": "string",
            "priority": "high|medium|low"
          }
        ]
      }
      
      Generate exactly 3-5 projects, prioritized by impact.
    `;

    const response = await this.generateText(prompt, 'upgrade-report-generation');

    try {
      const parsed = JSON.parse(response.text);
      
      // Validate projects array
      const projects = (parsed.projects || []).map((project: any) => ({
        name: project.name || 'Infrastructure Project',
        cost: Math.max(0, project.cost || 1000000),
        timeline: project.timeline || '6 months',
        description: project.description || 'Infrastructure improvement project',
        priority: ['high', 'medium', 'low'].includes(project.priority) 
          ? project.priority 
          : 'medium',
      }));

      return { projects };
    } catch (error) {
      logger.error('Failed to parse upgrade report response', error as Error, {
        responseText: response.text,
      });

      // Return fallback projects
      return {
        projects: [
          {
            name: 'Road Infrastructure Improvement',
            cost: 5000000,
            timeline: '1 year',
            description: 'Improve road connectivity and quality',
            priority: 'high',
          },
          {
            name: 'Water Supply Enhancement',
            cost: 3000000,
            timeline: '8 months',
            description: 'Expand water supply network',
            priority: 'high',
          },
          {
            name: 'Sanitation System Upgrade',
            cost: 2000000,
            timeline: '6 months',
            description: 'Improve drainage and sanitation',
            priority: 'medium',
          },
        ],
      };
    }
  }

  async generateHousingExplanation(
    familyProfile: any,
    housingUnit: any
  ): Promise<string> {
    const prompt = `
      Family profile: income ₹${familyProfile.monthlyIncome.toLocaleString('en-IN')}, 
      size ${familyProfile.householdSize} people, category ${familyProfile.category.toUpperCase()}.
      
      Unit details: ${housingUnit.specifications.bedrooms}BHK, ₹${housingUnit.financial.price.toLocaleString('en-IN')}, 
      area ${housingUnit.address.area}, ${housingUnit.scheme} scheme.
      
      Write a 2-sentence plain Hindi+English explanation of why this family qualifies 
      and what documents they need. Be specific and warm in tone.
      
      Example format: "आप ₹15,000 तक की आमदनी के साथ EWS श्रेणी के लिए योग्य हैं। आपको आधार कार्ड, आय प्रमाण पत्र, और पता प्रमाण जमा कराने होंगे।"
    `;

    return this.generateText(prompt, 'housing-explanation');
  }

  async detectBotIntent(message: string): Promise<{
    intent: 'FILE_COMPLAINT' | 'CHECK_STATUS' | 'FIND_HOUSING' | 'GREET' | 'UNKNOWN';
    entities: Record<string, unknown>;
  }> {
    const prompt = `
      User message: "${message}"
      
      Classify the intent as one of: FILE_COMPLAINT | CHECK_STATUS | FIND_HOUSING | GREET | UNKNOWN
      
      Extract any relevant entities like:
      - complaint_type (water, road, etc.)
      - phone_number
      - complaint_id
      - income_amount
      - family_size
      
      Return JSON with this exact structure:
      {
        "intent": "FILE_COMPLAINT|CHECK_STATUS|FIND_HOUSING|GREET|UNKNOWN",
        "entities": {
          "key": "value"
        }
      }
      
      Be conservative - if unsure, choose UNKNOWN.
    `;

    const response = await this.generateText(prompt, 'bot-intent-detection');

    try {
      const parsed = JSON.parse(response.text);
      
      return {
        intent: ['FILE_COMPLAINT', 'CHECK_STATUS', 'FIND_HOUSING', 'GREET', 'UNKNOWN'].includes(parsed.intent)
          ? parsed.intent
          : 'UNKNOWN',
        entities: parsed.entities || {},
      };
    } catch (error) {
      logger.error('Failed to parse bot intent response', error as Error, {
        responseText: response.text,
      });

      return {
        intent: 'UNKNOWN',
        entities: {},
      };
    }
  }

  // ============================================================================
  // Streaming Text Generation
  // ============================================================================

  async streamText(
    prompt: string,
    onChunk: (chunk: string) => void,
    context?: string
  ): Promise<string> {
    const fullPrompt = context ? `${context}\n\n${prompt}` : prompt;

    return withGeminiRetry(async () => {
      logger.debug('Starting Gemini text streaming', {
        promptLength: fullPrompt.length,
      });

      const result = await this.model.generateContentStream(fullPrompt);
      let fullText = '';

      for await (const chunk of result.stream) {
        const chunkText = chunk.text();
        fullText += chunkText;
        onChunk(chunkText);
      }

      logger.info('Gemini text streaming completed', {
        totalLength: fullText.length,
      });

      return fullText;
    }, 'streamText');
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  private calculateConfidence(response: any): number {
    // This is a simplified confidence calculation
    // In a real implementation, you might use more sophisticated methods
    
    if (response.candidates && response.candidates.length > 0) {
      const candidate = response.candidates[0];
      
      // Check finish reason
      if (candidate.finishReason === 'STOP') {
        return 0.9;
      } else if (candidate.finishReason === 'MAX_TOKENS') {
        return 0.7;
      } else if (candidate.finishReason === 'SAFETY') {
        return 0.5;
      }
    }
    
    return 0.6; // Default confidence
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  async healthCheck(): Promise<boolean> {
    try {
      const testPrompt = 'Respond with "OK" for health check.';
      const response = await this.generateText(testPrompt);
      return response.includes('OK');
    } catch (error) {
      logger.error('Gemini health check failed', error as Error);
      return false;
    }
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const geminiClient = new GeminiClient();
