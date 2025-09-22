# FREEDOM Castle GUI

A production-ready Next.js web cockpit for FREEDOM Platform operators.

## Overview

Castle GUI is the operator interface for the FREEDOM Platform, providing real-time monitoring, knowledge base management, and task execution capabilities. Built with Next.js 15, TypeScript, and Tailwind CSS for a modern, responsive experience.

## Features

### Core Functionality
- **Dashboard**: Real-time system health monitoring and status overview
- **Runs Management**: Submit knowledge base queries and view execution results
- **Knowledge Base**: Search existing knowledge and ingest new specifications
- **Service Health**: Monitor all platform services with detailed metrics
- **Settings**: Configure API connections and application preferences

### Technical Features
- **Real-time Updates**: WebSocket integration for live status updates
- **Responsive Design**: Optimized for desktop and mobile operator use
- **Error Handling**: Comprehensive error boundaries and user-friendly messages
- **Type Safety**: Full TypeScript implementation with strict type checking
- **API Integration**: Seamless connection to FREEDOM API Gateway (localhost:8080)

## Getting Started

### Development
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:3000
```

### Production Build
```bash
# Build for production
npm run build

# Start production server
npm start
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up castle-gui

# Access at http://localhost:3000
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Dashboard
│   ├── runs/              # Task runs management
│   ├── knowledge/         # Knowledge base interface
│   ├── services/          # Service health monitoring
│   └── settings/          # Configuration
├── components/            # Reusable UI components
│   ├── ui/               # Base UI components
│   └── layout/           # Layout components
├── lib/                  # Utilities and API clients
│   ├── api.ts            # API client functions
│   ├── websocket.ts      # WebSocket management
│   └── utils.ts          # Utility functions
└── providers/            # React context providers
```

## API Integration

Castle GUI connects to the FREEDOM API Gateway on `localhost:8080` with the following endpoints:

- `GET /health` - System health status
- `POST /kb/query` - Knowledge base search
- `POST /kb/ingest` - Specification ingestion
- `GET /metrics` - Prometheus metrics

Authentication is handled via API key (configurable in Settings).

## Environment Configuration

Create `.env.local` for local development:

```env
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_API_KEY=dev-key-change-in-production
NEXT_PUBLIC_WS_URL=ws://localhost:8080
```

## Testing

### End-to-End Tests
```bash
# Run Playwright tests
npm run test

# Run tests with UI
npm run test:ui
```

### Test Coverage
- Dashboard health monitoring
- Knowledge base search and ingestion
- Task runs management
- Service health monitoring
- Settings configuration
- Complete operator workflow validation

## Deployment

### Docker Production
```bash
# Build production image
docker build -t freedom-castle .

# Run container
docker run -p 3000:3000 freedom-castle
```

### Environment Variables
- `NEXT_PUBLIC_API_URL`: API Gateway endpoint
- `NEXT_PUBLIC_API_KEY`: Authentication key
- `NEXT_PUBLIC_WS_URL`: WebSocket endpoint
- `NODE_ENV`: Environment mode

## Verification

The Castle GUI includes comprehensive end-to-end tests that verify:

1. **Task Submission**: Can submit knowledge base queries
2. **Results Display**: Shows search results with proper formatting
3. **Health Monitoring**: Real-time system status updates
4. **Complete Workflow**: Full operator cycle from search to task completion

### Critical Test
The system includes a critical verification test that ensures:
- ✅ Can submit task (knowledge base query)
- ✅ Can see KB results (search responses)
- ✅ Can mark complete (task management)

This test validates the core operator workflow and confirms the system is operational.

## Architecture

### Technology Stack
- **Frontend**: Next.js 15 with App Router
- **Language**: TypeScript with strict type checking
- **Styling**: Tailwind CSS with custom components
- **State Management**: TanStack Query for server state
- **Real-time**: Socket.io for WebSocket connections
- **Testing**: Playwright for E2E testing
- **Deployment**: Docker with multi-stage builds

### Performance
- Static generation for optimal loading
- Incremental Static Regeneration (ISR)
- Code splitting and lazy loading
- Optimized bundle size (< 150KB)

## Development Guidelines

### Code Quality
- ESLint configuration with strict rules
- Prettier for code formatting
- TypeScript strict mode enabled
- Component-based architecture

### User Experience
- Loading states for all async operations
- Error boundaries with recovery options
- Responsive design for all screen sizes
- Accessibility compliance (WCAG 2.1)

## Health Monitoring

Castle GUI provides comprehensive health monitoring:

- **System Status**: Overall platform health
- **Service Metrics**: Individual service status and performance
- **Real-time Updates**: Live status changes
- **Historical Data**: Uptime and performance trends

## Knowledge Management

- **Search Interface**: Natural language queries
- **Result Display**: Detailed component specifications
- **Ingestion Form**: Add new specifications
- **Export Capabilities**: Download search results

## Security

- API key authentication
- CORS protection
- Input validation and sanitization
- Secure environment variable handling

## Support

For technical support and documentation:
- Check the FREEDOM Platform documentation
- Review API Gateway logs for connection issues
- Use browser dev tools for client-side debugging
- Run health checks to verify service connectivity

---

**FREEDOM Platform - Castle GUI v1.0.0**
*Production-ready operator cockpit for AI knowledge management*
