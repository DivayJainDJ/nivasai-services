# NivasAI Services

Firebase Cloud Functions monorepo for the NivasAI civic housing platform backend services.

## Overview

This repository contains 8 microservices that power the NivasAI platform:

- **complaint-classifier**: AI-powered complaint categorization using Gemini Vision
- **complaint-router**: Intelligent routing of complaints to ward officers
- **ward-analyzer**: Satellite imagery analysis for infrastructure assessment
- **housing-matcher**: PMAY housing unit matching algorithm
- **document-parser**: Automated document verification with Document AI
- **analytics-aggregator**: Real-time analytics and reporting
- **bot-webhook**: WhatsApp chatbot for citizen engagement
- **notification-broadcaster**: Multi-channel notification system

## Architecture

```
nivasai-services/
├── functions/
│   └── src/
│       ├── shared/           # Shared utilities and types
│       ├── complaint-classifier/
│       ├── complaint-router/
│       ├── ward-analyzer/
│       ├── housing-matcher/
│       ├── document-parser/
│       ├── analytics-aggregator/
│       ├── bot-webhook/
│       └── notification-broadcaster/
├── package.json
├── tsconfig.json
├── .eslintrc.js
├── firebase.json
└── .env.example
```

## Tech Stack

- **Runtime**: Node.js 20 + TypeScript
- **Framework**: Firebase Cloud Functions v2
- **AI**: Google Gemini 1.5 Pro SDK
- **Maps**: Google Maps Services JS
- **Messaging**: Twilio WhatsApp API
- **OCR**: Google Document AI
- **Analytics**: BigQuery SDK
- **Validation**: Zod
- **Queue**: Google Cloud Pub/Sub

## Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/nivasai-services.git
cd nivasai-services
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your actual API keys and configuration
```

4. Required environment variables:
- `GEMINI_API_KEY`: Google Gemini AI API key
- `GOOGLE_MAPS_KEY`: Google Maps API key
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `TWILIO_WHATSAPP_NUMBER`: Twilio WhatsApp number
- `DOCUMENT_AI_PROJECT_ID`: GCP project ID for Document AI
- `DOCUMENT_AI_LOCATION`: Document AI location (e.g., 'us')
- `DOCUMENT_AI_PROCESSOR_ID`: Document AI processor ID
- `BIGQUERY_DATASET`: BigQuery dataset name

## Local Development

1. Start Firebase emulators:
```bash
npm run serve
```

2. The emulators will start on:
- Functions: http://localhost:5001
- Firestore: http://localhost:8080
- Pub/Sub: http://localhost:8085
- Storage: http://localhost:9199
- Firebase UI: http://localhost:4000

3. Run tests:
```bash
npm test
```

4. Run linting:
```bash
npm run lint
```

## Deployment

Deploy to Firebase:
```bash
npm run deploy
```

## Services Documentation

### complaint-classifier

**Trigger**: Firestore onCreate on `/complaints/{complaintId}`

Analyzes new complaints using Gemini Vision API to categorize and assess severity.

**Flow**:
1. Downloads complaint photo from Cloud Storage
2. Sends photo + description to Gemini Vision
3. Parses JSON response with category, severity, summary
4. Updates complaint document with classification
5. Publishes event to Pub/Sub

### complaint-router

**Trigger**: Pub/Sub topic "complaint-classified"

Routes classified complaints to appropriate ward officers.

**Flow**:
1. Receives classified complaint data
2. Looks up ward officer mapping
3. Sends WhatsApp notification via Twilio
4. Sends FCM push notification
5. Logs routing event to BigQuery

### ward-analyzer

**Trigger**: HTTP POST `/analyzeWard`

Analyzes satellite imagery for infrastructure assessment.

**Flow**:
1. Fetches satellite tile from Maps Static API
2. Analyzes with Gemini Vision for infrastructure scores
3. Generates remediation plan with Gemini Text
4. Stores results in Firestore
5. Returns full analysis to caller

### housing-matcher

**Trigger**: HTTP POST `/matchHousing`

Matches families with available PMAY housing units.

**Flow**:
1. Fetches available housing units
2. Calculates match scores based on eligibility criteria
3. Uses Distance Matrix API for proximity scoring
4. Generates eligibility explanations with Gemini
5. Returns ranked matches

### document-parser

**Trigger**: Firestore onCreate on `/documentUploads/{docId}`

Parses and verifies uploaded documents using Document AI.

**Flow**:
1. Downloads document from Cloud Storage
2. Sends to Document AI for parsing
3. Extracts and validates key fields
4. Updates family profile with verified data
5. Sets document verification status

### analytics-aggregator

**Trigger**: Cloud Scheduler (hourly)

Aggregates analytics data and computes ward metrics.

**Flow**:
1. Queries Firestore for complaint and housing data
2. Calculates pressure scores per ward
3. Writes aggregated stats to BigQuery
4. Updates real-time dashboard metrics
5. Alerts on high-pressure wards

### bot-webhook

**Trigger**: HTTP POST `/whatsappWebhook`

Handles WhatsApp chatbot interactions.

**Flow**:
1. Parses incoming Twilio message
2. Detects intent using Gemini
3. Routes to appropriate intent handler
4. Sends response via Twilio API
5. Logs conversation session

### notification-broadcaster

**Trigger**: Pub/Sub topic "broadcast-notification"

Broadcasts notifications to targeted user groups.

**Flow**:
1. Receives notification payload
2. Fetches FCM tokens for recipients
3. Sends multicast FCM notifications
4. Logs delivery status
5. Cleans up expired tokens

## Shared Utilities

The `/functions/src/shared/` directory contains common utilities:

- `geminiClient.ts`: Gemini AI client with retry wrapper
- `firestoreAdmin.ts`: Firestore admin SDK instance
- `storageAdmin.ts`: Cloud Storage admin utilities
- `mapsClient.ts`: Google Maps services client
- `twilioClient.ts`: Twilio REST client
- `bigqueryClient.ts`: BigQuery client and helpers
- `logger.ts`: Structured Cloud Logging wrapper
- `types.ts`: Shared TypeScript interfaces
- `validators.ts`: Zod validation schemas
- `retryHelper.ts`: Exponential backoff wrapper

## Testing

Each service includes comprehensive unit tests that mock external dependencies:

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

Tests mock:
- Firebase Admin SDK
- Gemini AI API
- Twilio API
- Google Maps API
- Document AI API
- BigQuery API

## Monitoring

- **Cloud Logging**: All functions use structured logging
- **Error Reporting**: Automatic error capture and reporting
- **Performance Monitoring**: Firebase Performance SDK integration
- **BigQuery Analytics**: Custom analytics tables for insights

## Security

- All API keys stored in environment variables
- Input validation with Zod schemas
- Rate limiting on external API calls
- Secure file handling in Cloud Storage
- FCM token validation and cleanup

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run linting and tests
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
